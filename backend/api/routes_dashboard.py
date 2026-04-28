"""
Routes dashboard v2 — avec stats CSAT integrees.
"""
from datetime import datetime, timezone
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.mocks.crm_api import lister_tous_tickets, obtenir_stats_csat
from backend.mocks.notifications import lister_notifications
from backend.mocks.ussd_api import lister_sessions_ussd
from backend.api.routes_chat import nb_connexions_actives

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/metriques")
async def obtenir_metriques():
    """Metriques principales + CSAT pour le dashboard operateur."""
    res_tickets = lister_tous_tickets()
    tickets = res_tickets.get("tickets", [])

    total = len(tickets)
    ouverts  = [t for t in tickets if t["statut"] == "ouvert"]
    resolus  = [t for t in tickets if t["statut"] == "resolu"]
    en_cours = [t for t in tickets if t["statut"] == "en_cours"]
    p1 = [t for t in tickets if t["priorite"] == "P1"]
    p2 = [t for t in tickets if t["priorite"] == "P2"]

    taux = round(len(resolus) / total * 100, 1) if total > 0 else 0

    types: dict[str, int] = {}
    canaux: dict[str, int] = {}
    for t in tickets:
        typ = t.get("type_reclamation", "inconnu")
        types[typ] = types.get(typ, 0) + 1
        canal = t.get("canal_origine", "inconnu")
        canaux[canal] = canaux.get(canal, 0) + 1

    csat = obtenir_stats_csat()

    return {
        "horodatage": datetime.now(timezone.utc).isoformat(),
        "kpis": {
            "total_tickets": total,
            "tickets_ouverts": len(ouverts),
            "tickets_resolus": len(resolus),
            "tickets_en_cours": len(en_cours),
            "incidents_p1": len(p1),
            "incidents_p2": len(p2),
            "taux_resolution_pct": taux,
            "sessions_actives": nb_connexions_actives(),
        },
        "csat": csat,
        "repartition_types": types,
        "repartition_canaux": canaux,
        "tickets_recents": tickets[:15],
    }


@router.get("/tickets")
async def lister_tickets(statut: str = None, priorite: str = None):
    res = lister_tous_tickets(statut=statut)
    tickets = res.get("tickets", [])
    if priorite:
        tickets = [t for t in tickets if t.get("priorite") == priorite]
    return {"tickets": tickets, "total": len(tickets)}


@router.get("/csat")
async def obtenir_csat():
    """Retourne les statistiques CSAT detaillees."""
    return obtenir_stats_csat()


@router.get("/tickets/p1")
async def tickets_p1():
    res = lister_tous_tickets()
    p1 = [t for t in res.get("tickets", []) if t["priorite"] == "P1"]
    return {"tickets": p1, "total": len(p1)}


@router.post("/csat/{id_ticket}")
async def soumettre_csat(id_ticket: str, note: int, commentaire: str = ""):
    """Endpoint pour soumettre une note CSAT depuis le frontend."""
    from backend.mocks.crm_api import enregistrer_csat
    res = enregistrer_csat(id_ticket, note, commentaire)
    return res


@router.get("/sante")
async def sante():
    return {
        "statut": "ok",
        "horodatage": datetime.now(timezone.utc).isoformat(),
        "sessions_actives": nb_connexions_actives(),
    }
