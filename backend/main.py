"""
main.py — Point d'entree FastAPI v2.
Initialise tous les services au demarrage et enregistre les routers.
"""
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.api.routes_chat import router as router_chat
from backend.api.routes_dashboard import router as router_dashboard
from backend.api.routes_canaux import router as router_canaux
from ai_core.dialogue.context_manager import GestionnaireContexte
from ai_core.dialogue.orchestrateur import init_orchestrateur


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialisation au demarrage de l'app :
    1. Connexion Redis
    2. Init GestionnaireContexte
    3. Init Orchestrateur (charge Gemini + system prompt)
    """
    print("[BOOT] Demarrage Agent IA Support Telco v2...")

    # Redis
    try:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        print(f"[BOOT] Redis connecte : {settings.redis_url}")
    except Exception as e:
        print(f"[BOOT] Redis indisponible ({e}) — sessions en memoire uniquement")
        redis_client = None

    # Gestionnaire de contexte
    gestionnaire = GestionnaireContexte(redis_client=redis_client)
    app.state.gestionnaire = gestionnaire

    # Orchestrateur
    try:
        orchestrateur = init_orchestrateur(gestionnaire)
        app.state.orchestrateur = orchestrateur
        print("[BOOT] Orchestrateur IA initialise (Gemini 2.5 Flash)")
    except Exception as e:
        print(f"[BOOT] Erreur orchestrateur : {e}")

    print("[BOOT] Agent IA pret. Swagger : http://localhost:8000/docs")
    yield

    # Nettoyage a l'arret
    if redis_client:
        await redis_client.close()
    print("[SHUTDOWN] Agent IA arrete proprement.")


app = FastAPI(
    title="Agent IA Support Telco — Mobile Money UEMOA",
    description=(
        "Agent conversationnel IA omnicanal pour le support client "
        "Mobile Money en zone UEMOA. "
        "Operateurs : Wave, Orange Money, Mixx by Yas."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(router_chat, prefix="/api/v1")
app.include_router(router_dashboard, prefix="/api/v1")
app.include_router(router_canaux, prefix="/api/v1")


@app.get("/", tags=["Sante"])
async def racine():
    return {
        "service": "Agent IA Support Telco — Mobile Money UEMOA",
        "version": "2.0.0",
        "statut": "ok",
        "docs": "/docs",
        "canaux": ["WebSocket /api/v1/chat/ws/{session}/{telephone}", "REST /api/v1/chat/message", "WhatsApp /api/v1/canaux/whatsapp/webhook", "USSD /api/v1/canaux/ussd", "Email /api/v1/canaux/email/entrant"],
    }


@app.get("/health", tags=["Sante"])
async def health():
    return {"statut": "ok", "version": "2.0.0"}