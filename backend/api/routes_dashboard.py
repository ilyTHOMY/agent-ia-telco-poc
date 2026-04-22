"""
Routes dashboard — metriques operateur en temps reel.
Expose les KPIs, tickets, sessions actives et statistiques.
"""
from datetime import datetime, timezone
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.mocks.crm_api import lister_tous_tickets
from backend.mocks.notifications import lister_notifications
from backend.mocks.ussd_api import lister_sessions_ussd
from backend.api.routes_chat import nb_connexions_actives

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/metriques")
async def obtenir_metriques():
    """
    Retourne les metriques principales du dashboard operateur.
    Polling toutes les 5 secondes depuis le frontend.
    """
    res_tickets = lister_tous_tickets()
    tickets = res_tickets.get("tickets", [])

    # Calculs KPIs
    total = len(tickets)
    ouverts = [t for t in tickets if t["statut"] == "ouvert"]
    resolus = [t for t in tickets if t["statut"] == "resolu"]
    en_cours = [t for t in tickets if t["statut"] == "en_cours"]
    p1 = [t for t in tickets if t["priorite"] == "P1"]
    p2 = [t for t in tickets if t["priorite"] == "P2"]

    taux_resolution = round(len(resolus) / total * 100, 1) if total > 0 else 0

    # Repartition par type
    types: dict[str, int] = {}
    for t in tickets:
        typ = t.get("type_reclamation", "inconnu")
        types[typ] = types.get(typ, 0) + 1

    # Repartition par canal
    canaux: dict[str, int] = {}
    for t in tickets:
        canal = t.get("canal_origine", "inconnu")
        canaux[canal] = canaux.get(canal, 0) + 1

    return {
        "horodatage": datetime.now(timezone.utc).isoformat(),
        "kpis": {
            "total_tickets": total,
            "tickets_ouverts": len(ouverts),
            "tickets_resolus": len(resolus),
            "tickets_en_cours": len(en_cours),
            "incidents_p1": len(p1),
            "incidents_p2": len(p2),
            "taux_resolution_pct": taux_resolution,
            "sessions_actives": nb_connexions_actives(),
        },
        "repartition_types": types,
        "repartition_canaux": canaux,
        "tickets_recents": tickets[:10],
    }


@router.get("/tickets")
async def lister_tickets(statut: str = None, priorite: str = None):
    """Liste tous les tickets avec filtres optionnels."""
    res = lister_tous_tickets(statut=statut)
    tickets = res.get("tickets", [])
    if priorite:
        tickets = [t for t in tickets if t.get("priorite") == priorite]
    return {"tickets": tickets, "total": len(tickets)}


@router.get("/tickets/p1")
async def tickets_priorite_1():
    """Retourne uniquement les tickets P1 (urgents)."""
    res = lister_tous_tickets()
    p1 = [t for t in res.get("tickets", []) if t["priorite"] == "P1"]
    return {"tickets": p1, "total": len(p1)}


@router.get("/notifications")
async def obtenir_notifications():
    """Retourne toutes les notifications envoyees."""
    res = lister_notifications()
    return res


@router.get("/sessions-ussd")
async def obtenir_sessions_ussd():
    """Retourne les sessions USSD actives et terminees."""
    return lister_sessions_ussd()


@router.get("/sante")
async def sante_systeme():
    """Healthcheck etendu pour le dashboard."""
    return {
        "statut": "ok",
        "horodatage": datetime.now(timezone.utc).isoformat(),
        "services": {
            "api": "ok",
            "sessions_actives": nb_connexions_actives(),
        }
    }