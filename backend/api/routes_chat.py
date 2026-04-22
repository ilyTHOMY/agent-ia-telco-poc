"""
Routes chat — WebSocket temps reel + REST.
Gere la connexion, l'authentification et le flux de messages.
"""
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ai_core.dialogue.orchestrateur import get_orchestrateur

router = APIRouter(prefix="/chat", tags=["Chat"])

# Stockage des connexions WebSocket actives
connexions_actives: dict[str, WebSocket] = {}


# ── Modeles Pydantic ───────────────────────────────────────────────────────────

class DemandeNouvelleSession(BaseModel):
    telephone: str
    canal: str = "chat"


class DemandeMessage(BaseModel):
    id_session: str
    telephone: str
    message: str
    canal: str = "chat"


# ── REST ───────────────────────────────────────────────────────────────────────

@router.get("/nouvelle-session")
async def nouvelle_session(telephone: str, canal: str = "chat"):
    """Cree une nouvelle session de conversation."""
    id_session = str(uuid.uuid4())
    return {
        "id_session": id_session,
        "telephone": telephone,
        "canal": canal,
        "message": "Session creee. Veuillez entrer votre PIN pour vous authentifier.",
        "authentification_requise": True,
    }


@router.post("/message")
async def envoyer_message_rest(demande: DemandeMessage):
    """
    Envoie un message via REST (fallback si WebSocket indisponible).
    Utilise par les canaux email et USSD.
    """
    try:
        orchestrateur = get_orchestrateur()
        resultat = await orchestrateur.traiter_message(
            id_session=demande.id_session,
            telephone=demande.telephone,
            message=demande.message,
            canal=demande.canal,
        )
        return JSONResponse(content=resultat)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{id_session}")
async def obtenir_session(id_session: str):
    """Retourne l'etat d'une session existante."""
    try:
        orchestrateur = get_orchestrateur()
        ctx = await orchestrateur.gestionnaire.obtenir(id_session)
        if not ctx:
            raise HTTPException(status_code=404, detail="Session introuvable")
        return {
            "id_session": id_session,
            "telephone": ctx.telephone,
            "authentifie": ctx.authentifie,
            "langue": ctx.langue,
            "nb_messages": len(ctx.historique),
            "tickets": ctx.tickets_crees,
            "escalade_effectuee": ctx.escalade_effectuee,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── WebSocket ──────────────────────────────────────────────────────────────────

@router.websocket("/ws/{id_session}/{telephone}")
async def websocket_chat(websocket: WebSocket, id_session: str, telephone: str):
    """
    WebSocket principal pour le chat temps reel.
    URL : ws://localhost:8000/chat/ws/{id_session}/{telephone}
    """
    await websocket.accept()
    connexions_actives[id_session] = websocket

    try:
        orchestrateur = get_orchestrateur()

        # Message de bienvenue
        await websocket.send_json({
            "type": "connexion",
            "message": "Connexion etablie. Veuillez entrer votre PIN pour vous identifier.",
            "id_session": id_session,
        })

        while True:
            # Recevoir message du client
            data = await websocket.receive_json()
            message = data.get("message", "").strip()

            if not message:
                continue

            # Indicateur de frappe
            await websocket.send_json({"type": "frappe", "contenu": "..."})

            # Traiter via orchestrateur
            resultat = await orchestrateur.traiter_message(
                id_session=id_session,
                telephone=telephone,
                message=message,
                canal="chat",
            )

            # Envoyer reponse
            await websocket.send_json({
                "type": "reponse",
                **resultat,
            })

            # Si escalade P1, fermer proprement apres notification
            if resultat.get("priorite") == "P1":
                await websocket.send_json({
                    "type": "info",
                    "message": "Votre dossier est pris en charge en urgence. La conversation est transferee.",
                })

    except WebSocketDisconnect:
        connexions_actives.pop(id_session, None)
        print(f"[WS] Client deconnecte : {id_session}")
    except Exception as e:
        print(f"[WS] Erreur session {id_session} : {e}")
        connexions_actives.pop(id_session, None)
        try:
            await websocket.send_json({"type": "erreur", "message": str(e)})
        except Exception:
            pass


def nb_connexions_actives() -> int:
    return len(connexions_actives)