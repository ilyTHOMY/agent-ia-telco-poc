"""
Routes canaux — WhatsApp webhook, USSD, Email entrant.
Chaque canal transforme sa requete en appel vers l'orchestrateur.
"""
import uuid
import hmac
import hashlib
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel

from ai_core.dialogue.orchestrateur import get_orchestrateur
from backend.mocks.whatsapp_api import recevoir_message as wa_recevoir, envoyer_message as wa_envoyer
from backend.mocks.ussd_api import traiter_requete_ussd
from backend.mocks.email_api import envoyer_email
from backend.config import settings

router = APIRouter(prefix="/canaux", tags=["Canaux"])


# ══════════════════════════════════════════════════════════════════════════════
# WHATSAPP
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/whatsapp/webhook")
async def whatsapp_webhook_verification(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """
    Verification du webhook Meta (etape obligatoire pour activer l'API).
    Meta envoie une requete GET avec un challenge a retourner.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return PlainTextResponse(hub_challenge or "")
    raise HTTPException(status_code=403, detail="Token de verification invalide")


@router.post("/whatsapp/webhook")
async def whatsapp_webhook_reception(request: Request):
    """
    Reception des messages WhatsApp entrants depuis Meta.
    Chaque message est traite par l'orchestrateur et la reponse est renvoyee via WhatsApp.
    """
    body = await request.json()

    try:
        # Parser le payload Meta
        entree = body.get("entry", [{}])[0]
        changements = entree.get("changes", [{}])[0]
        valeur = changements.get("value", {})
        messages = valeur.get("messages", [])

        for msg in messages:
            if msg.get("type") != "text":
                continue

            telephone = msg["from"]
            texte = msg["text"]["body"]
            wa_id = msg.get("id", "")

            # Enregistrer dans le mock
            wa_recevoir(telephone, texte)

            # Generer ou recuperer l'ID de session WhatsApp
            id_session = f"wa_{telephone}"

            # Traiter via orchestrateur
            orchestrateur = get_orchestrateur()
            resultat = await orchestrateur.traiter_message(
                id_session=id_session,
                telephone=f"+{telephone}" if not telephone.startswith("+") else telephone,
                message=texte,
                canal="whatsapp",
            )

            # Repondre via WhatsApp
            wa_envoyer(telephone, resultat["reponse"])

    except Exception as e:
        print(f"[WA WEBHOOK] Erreur : {e}")

    # Meta exige toujours un 200 OK
    return JSONResponse(content={"status": "ok"})


# ══════════════════════════════════════════════════════════════════════════════
# USSD
# ══════════════════════════════════════════════════════════════════════════════

class RequeteUSSD(BaseModel):
    sessionId: str
    phoneNumber: str
    text: str
    serviceCode: str = "*144#"


@router.post("/ussd")
async def ussd_handler(requete: RequeteUSSD):
    """
    Handler USSD compatible AfricasTalking.
    Retourne une reponse au format texte prefixee par CON (continue) ou END (fin).
    """
    resultat = traiter_requete_ussd(
        session_id=requete.sessionId,
        telephone=requete.phoneNumber,
        texte=requete.text,
        code_service=requete.serviceCode,
    )

    reponse_texte = resultat.get("reponse", "END Service momentanement indisponible.")

    # Si l'utilisateur a selectionne "Parler a un conseiller" via USSD
    if requete.text == "4":
        id_session = f"ussd_{requete.sessionId}"
        orchestrateur = get_orchestrateur()
        res = await orchestrateur.traiter_message(
            id_session=id_session,
            telephone=requete.phoneNumber,
            message="je veux parler a un conseiller",
            canal="ussd",
        )
        ticket_id = res.get("id_ticket", "")
        if ticket_id:
            reponse_texte = f"END Transfert en cours. Votre reference : {ticket_id}. Rappel sous 5 min."

    return PlainTextResponse(content=reponse_texte)


# ══════════════════════════════════════════════════════════════════════════════
# EMAIL
# ══════════════════════════════════════════════════════════════════════════════

class EmailEntrant(BaseModel):
    expediteur: str
    sujet: str
    corps: str
    telephone: str = ""


@router.post("/email/entrant")
async def email_entrant(email: EmailEntrant):
    """
    Traite un email entrant comme une reclamation.
    Extrait le telephone depuis le corps ou l'expediteur si fourni.
    """
    telephone = email.telephone or email.expediteur
    id_session = f"email_{str(uuid.uuid4())[:8]}"

    # Message combine pour l'orchestrateur
    message = f"Objet: {email.sujet}\n\n{email.corps}"

    orchestrateur = get_orchestrateur()
    resultat = await orchestrateur.traiter_message(
        id_session=id_session,
        telephone=telephone,
        message=message,
        canal="email",
    )

    # Repondre par email
    envoyer_email(
        destinataire=email.expediteur,
        sujet=f"Re: {email.sujet}",
        corps_texte=resultat["reponse"],
        id_ticket=resultat.get("id_ticket"),
    )

    return {"traite": True, "reponse": resultat["reponse"], "id_ticket": resultat.get("id_ticket")}