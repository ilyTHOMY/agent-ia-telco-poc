import uuid
import asyncio
import traceback
from urllib.parse import unquote
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ai_core.dialogue.orchestrateur import get_orchestrateur

router = APIRouter(prefix="/chat", tags=["Chat"])
connexions_actives: dict[str, WebSocket] = {}


class DemandeMessage(BaseModel):
    id_session: str
    telephone: str
    message: str
    canal: str = "chat"


async def _attendre_orchestrateur(timeout: int = 60):
    for _ in range(timeout * 2):
        try:
            get_orchestrateur()
            return True
        except RuntimeError:
            await asyncio.sleep(0.5)
    return False


@router.get("/nouvelle-session")
async def nouvelle_session(canal: str = "chat"):
    id_session = str(uuid.uuid4())
    return {"id_session": id_session, "canal": canal}


@router.post("/message")
async def envoyer_message_rest(demande: DemandeMessage):
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


@router.websocket("/ws/{id_session}/{telephone}")
async def websocket_chat(websocket: WebSocket, id_session: str, telephone: str):
    await websocket.accept()
    connexions_actives[id_session] = websocket
    telephone_decode = unquote(telephone).replace(" ", "")
    print(f"[WS DEBUG] Connexion : {id_session} | tel={telephone_decode}")

    try:
        print(f"[WS DEBUG] Attente orchestrateur...")
        pret = await _attendre_orchestrateur(timeout=60)
        print(f"[WS DEBUG] Orchestrateur pret={pret}")

        if not pret:
            await websocket.send_json({
                "type": "erreur",
                "message": "Le serveur demarre encore. Reessayez dans quelques secondes."
            })
            await websocket.close()
            return

        orchestrateur = get_orchestrateur()
        print(f"[WS DEBUG] Orchestrateur OK")

        ctx = await orchestrateur.gestionnaire.obtenir(id_session)
        print(f"[WS DEBUG] Contexte obtenu : {ctx}")

        if not ctx:
            ctx = await orchestrateur.gestionnaire.creer(id_session, telephone_decode, "chat")
            ctx.telephone = telephone_decode
            await orchestrateur.gestionnaire.sauvegarder(ctx)
            print(f"[WS DEBUG] Contexte cree pour {telephone_decode}")

        await websocket.send_json({
            "type": "connexion",
            "message": "Connecte. Entrez votre PIN.",
            "id_session": id_session,
        })
        print(f"[WS DEBUG] Message connexion envoye")

        while True:
            data = await websocket.receive_json()
            message = data.get("message", "").strip()
            print(f"[WS DEBUG] Message recu : '{message}'")

            if not message:
                continue

            await websocket.send_json({"type": "frappe"})

            print(f"[WS DEBUG] Appel traiter_message...")
            resultat = await orchestrateur.traiter_message(
                id_session=id_session,
                telephone=telephone_decode,
                message=message,
                canal="chat",
            )
            print(f"[WS DEBUG] Resultat : {str(resultat)[:100]}")

            await websocket.send_json({"type": "reponse", **resultat})

            if resultat.get("priorite") == "P1":
                await websocket.send_json({
                    "type": "info",
                    "message": "Votre dossier est pris en charge en urgence.",
                })

    except WebSocketDisconnect:
        print(f"[WS] Deconnecte : {id_session}")
        connexions_actives.pop(id_session, None)
    except Exception as e:
        print(f"[WS] Erreur {id_session} : {e}")
        traceback.print_exc()
        connexions_actives.pop(id_session, None)
        try:
            await websocket.send_json({"type": "erreur", "message": str(e)})
        except Exception:
            pass


def nb_connexions_actives() -> int:
    return len(connexions_actives)