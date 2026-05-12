"""
Canal Telegram v2 — flux auth complet via orchestrateur.
Le telephone est collecte dans la conversation, pas depuis l'URL.
"""
import os
import httpx
from fastapi import APIRouter, Request

from ai_core.dialogue.orchestrateur import get_orchestrateur

router = APIRouter(prefix="/canaux/telegram", tags=["Telegram"])

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


async def envoyer_message(chat_id: int, texte: str):
    if not TELEGRAM_TOKEN:
        print("[TELEGRAM] Token manquant dans .env")
        return
    texte_propre = texte.replace("**", "*")
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": texte_propre,
            "parse_mode": "Markdown",
        })


@router.post("/webhook")
async def webhook_telegram(request: Request):
    try:
        data = await request.json()
    except Exception:
        return {"ok": True}

    message = data.get("message", {})
    if not message:
        return {"ok": True}

    chat_id = message.get("chat", {}).get("id")
    texte   = message.get("text", "").strip()

    if not chat_id or not texte:
        return {"ok": True}

    # Commande /start
    if texte == "/start":
        await envoyer_message(chat_id,
            "Bienvenue sur le support Mobile Money UEMOA 🤖\n\n"
            "Entrez votre numéro de téléphone au format :\n"
            "*+221 XX XXX XX XX*\n\n"
            "Exemple : +221771234567"
        )
        return {"ok": True}

    if texte.startswith("/"):
        return {"ok": True}

    id_session = f"telegram_{chat_id}"

    try:
        orchestrateur = get_orchestrateur()

        # Recuperer ou creer le contexte
        ctx = await orchestrateur.gestionnaire.obtenir(id_session)
        if not ctx:
            ctx = await orchestrateur.gestionnaire.creer(id_session, "", "telegram")
            await orchestrateur.gestionnaire.sauvegarder(ctx)

        # Determiner le telephone a utiliser
        telephone = ctx.telephone if ctx and ctx.telephone else ""

        resultat = await orchestrateur.traiter_message(
            id_session=id_session,
            telephone=telephone,
            message=texte,
            canal="telegram",
        )

        reponse = resultat.get("reponse", "")
        if reponse:
            await envoyer_message(chat_id, reponse)

        if resultat.get("id_ticket"):
            await envoyer_message(chat_id,
                f"📋 Référence ticket : `{resultat['id_ticket']}`"
            )

    except Exception as e:
        print(f"[TELEGRAM] Erreur : {e}")
        await envoyer_message(chat_id,
            "Une erreur technique est survenue. Veuillez réessayer."
        )

    return {"ok": True}


@router.get("/info")
async def info_bot():
    if not TELEGRAM_TOKEN:
        return {"erreur": "TELEGRAM_BOT_TOKEN manquant dans .env"}
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{TELEGRAM_API}/getMe")
        return res.json()
