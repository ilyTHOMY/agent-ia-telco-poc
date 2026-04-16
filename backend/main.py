from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Agent IA Support Telco — PoC v2",
    description="Agent conversationnel IA Mobile Money UEMOA",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"statut": "ok", "version": "2.0.0"}

@app.get("/")
async def racine():
    return {
        "message": "Agent IA Support Telco — PoC v2",
        "docs": "/docs",
        "websocket": "ws://localhost:8000/api/v1/ws/chat/{id_session}",
    }

# Routers — a importer au fur et a mesure
# from backend.api import routes_chat, routes_dashboard, routes_rapports, routes_canaux
# app.include_router(routes_chat.router, prefix="/api/v1")
# app.include_router(routes_dashboard.router, prefix="/api/v1")
# app.include_router(routes_rapports.router, prefix="/api/v1")
# app.include_router(routes_canaux.router, prefix="/api/v1")
