"""
Canal Telegram v4 — flux auth complet avec gestion nouveau client.
"""
import os
import httpx
from fastapi import APIRouter, Request

from ai_core.dialogue.orchestrateur import get_orchestrateur

router = APIRouter(prefix="/canaux/telegram", tags=["Telegram"])

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

_tg_sessions: dict[int, dict] = {}


async def envoyer_message(chat_id: int, texte: str):
    if not TELEGRAM_TOKEN:
        return
    texte_propre = texte.replace("**", "*")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"{TELEGRAM_API}/sendMessage", json={
                "chat_id": chat_id,
                "text": texte_propre,
                "parse_mode": "Markdown",
            })
    except Exception as e:
        print(f"[TELEGRAM] Erreur envoi : {e}")


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

    # ── /start ────────────────────────────────────────────────────────────────
    if texte == "/start":
        _tg_sessions[chat_id] = {"etape": "telephone"}
        await envoyer_message(chat_id,
            "Bienvenue sur le support *Mobile Money UEMOA* 🤖\n\n"
            "Entrez votre numéro de téléphone :\n"
            "*+221 XX XXX XX XX*\n\n"
            "_Exemple : +221771234567_"
        )
        return {"ok": True}

    if texte.startswith("/"):
        return {"ok": True}

    session = _tg_sessions.get(chat_id, {"etape": "telephone"})
    etape = session.get("etape", "telephone")

    # ── Etape 1 : Telephone ───────────────────────────────────────────────────
    if etape == "telephone":
        telephone = texte.replace(" ", "")
        if len(telephone) < 8:
            await envoyer_message(chat_id,
                "Numéro invalide. Format attendu :\n*+221 XX XXX XX XX*")
            return {"ok": True}
        _tg_sessions[chat_id] = {"etape": "pin", "telephone": telephone}
        await envoyer_message(chat_id, "Entrez votre code PIN à 4 chiffres :")
        return {"ok": True}

    # ── Etape 2 : PIN ─────────────────────────────────────────────────────────
    if etape == "pin":
        pin = texte.strip()
        telephone = session.get("telephone", "")

        if len(pin) != 4 or not pin.isdigit():
            await envoyer_message(chat_id, "Le PIN doit contenir exactement 4 chiffres.")
            return {"ok": True}

        try:
            orchestrateur = get_orchestrateur()
            id_session = f"telegram_{chat_id}"

            ctx = await orchestrateur.gestionnaire.obtenir(id_session)
            if not ctx:
                ctx = await orchestrateur.gestionnaire.creer(id_session, telephone, "telegram")
            ctx.telephone = telephone
            await orchestrateur.gestionnaire.sauvegarder(ctx)

            resultat = await orchestrateur.traiter_message(
                id_session=id_session,
                telephone=telephone,
                message=pin,
                canal="telegram",
            )

            reponse = resultat.get("reponse", "")

            if resultat.get("authentifie"):
                # Client existant — conversation directe
                _tg_sessions[chat_id] = {
                    "etape": "conversation",
                    "telephone": telephone,
                }
            elif resultat.get("nouveau_client"):
                # Nouveau client — orchestrateur va demander le nom
                # On passe directement en conversation
                _tg_sessions[chat_id] = {
                    "etape": "conversation",
                    "telephone": telephone,
                }
            else:
                # Mauvais PIN ou compte bloque
                _tg_sessions[chat_id]["etape"] = "pin"

            if reponse:
                await envoyer_message(chat_id, reponse)

        except Exception as e:
            print(f"[TELEGRAM] Erreur auth : {e}")
            await envoyer_message(chat_id,
                "Erreur technique. Tapez /start pour recommencer.")

        return {"ok": True}

    # ── Etape 3 : Conversation ────────────────────────────────────────────────
    if etape == "conversation":
        telephone = session.get("telephone", "")
        id_session = f"telegram_{chat_id}"

        try:
            orchestrateur = get_orchestrateur()
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
                    f"📋 Référence ticket : `{resultat['id_ticket']}`")

        except Exception as e:
            print(f"[TELEGRAM] Erreur conversation : {e}")
            await envoyer_message(chat_id, "Erreur technique. Veuillez réessayer.")

        return {"ok": True}

    # Fallback
    _tg_sessions[chat_id] = {"etape": "telephone"}
    await envoyer_message(chat_id, "Tapez /start pour commencer.")
    return {"ok": True}


@router.get("/info")
async def info_bot():
    if not TELEGRAM_TOKEN:
        return {"erreur": "TELEGRAM_BOT_TOKEN manquant"}
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{TELEGRAM_API}/getMe")
        return res.json()
