"""
main.py v3 — Point d'entree FastAPI final.
Tous les imports mis a jour : crm v2, mobile_money v3, orchestrateur v2, routes_chat v2.
"""
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.api.routes_chat import router as router_chat
from backend.api.routes_dashboard import router as router_dashboard
from backend.api.routes_canaux import router as router_canaux
from backend.api.routes_rapports import router as router_rapports
from ai_core.dialogue.context_manager import GestionnaireContexte
from ai_core.dialogue.orchestrateur import init_orchestrateur


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[BOOT] Demarrage Agent IA Support Telco v2...")

    # Redis
    redis_client = None
    try:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        print(f"[BOOT] Redis OK : {settings.redis_url}")
    except Exception as e:
        print(f"[BOOT] Redis indisponible ({e}) — sessions en memoire")

    # Gestionnaire de contexte
    gestionnaire = GestionnaireContexte(redis_client=redis_client)
    app.state.gestionnaire = gestionnaire

    # Orchestrateur
    try:
        orchestrateur = init_orchestrateur(gestionnaire)
        app.state.orchestrateur = orchestrateur
        print("[BOOT] Orchestrateur IA pret (Gemini 2.5 Flash)")
    except Exception as e:
        print(f"[BOOT] Erreur orchestrateur : {e}")

    print("[BOOT] Agent IA pret.")
    print("[BOOT] Frontend  : http://localhost:3000")
    print("[BOOT] Swagger   : http://localhost:8000/docs")
    print("[BOOT] Qdrant    : http://localhost:6333/dashboard")

    yield

    if redis_client:
        await redis_client.close()
    print("[SHUTDOWN] Arret propre.")


app = FastAPI(
    title="Agent IA Support Telco — Mobile Money UEMOA",
    description="Agent conversationnel IA omnicanal — Wave · Orange Money · Mixx by Yas",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_chat,      prefix="/api/v1")
app.include_router(router_dashboard, prefix="/api/v1")
app.include_router(router_canaux,    prefix="/api/v1")
app.include_router(router_rapports,  prefix="/api/v1")


@app.get("/", tags=["Sante"])
async def racine():
    return {
        "service": "Agent IA Support Telco — Mobile Money UEMOA",
        "version": "2.0.0",
        "statut": "ok",
        "docs": "/docs",
        "canaux": [
            "WebSocket : ws://localhost:8000/api/v1/chat/ws/{id_session}",
            "REST      : POST /api/v1/chat/message",
            "WhatsApp  : POST /api/v1/canaux/whatsapp/webhook",
            "USSD      : POST /api/v1/canaux/ussd",
            "Email     : POST /api/v1/canaux/email/entrant",
        ],
    }


@app.get("/health", tags=["Sante"])
async def health():
    return {"statut": "ok", "version": "2.0.0"}
