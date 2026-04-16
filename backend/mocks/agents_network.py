"""
Mock API Reseau Agents — simule la gestion du reseau d'agents Mobile Money.
Inclut la geolocalisation (haversine), la disponibilite et le signalement.
"""
import json
import math
from pathlib import Path
from datetime import datetime, timezone

DONNEES_DIR = Path(__file__).parent.parent.parent / "data"


def _charger_agents() -> list:
    with open(DONNEES_DIR / "agents.json", encoding="utf-8") as f:
        return json.load(f)["agents"]


def _horodatage() -> str:
    return datetime.now(timezone.utc).isoformat()


def _distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance haversine entre deux points GPS."""
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(d_lng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def obtenir_agent(id_agent: str) -> dict:
    """Retourne les details d'un agent par son ID."""
    for agent in _charger_agents():
        if agent["id"] == id_agent:
            return {"succes": True, "agent": agent}
    return {"succes": False, "erreur": "Agent introuvable"}


def lister_agents_proches(
    latitude: float,
    longitude: float,
    operateur: str = None,
    rayon_km: float = 5.0,
) -> dict:
    """Retourne les agents actifs dans un rayon, tries par distance."""
    resultats = []
    for agent in _charger_agents():
        if agent["statut"] != "en_ligne":
            continue
        if operateur and agent["operateur"] != operateur:
            continue
        loc = agent["localisation"]
        distance = _distance_km(latitude, longitude, loc["latitude"], loc["longitude"])
        if distance <= rayon_km:
            resultats.append({**agent, "distance_km": round(distance, 2)})
    resultats.sort(key=lambda a: a["distance_km"])
    return {
        "succes": True,
        "agents": resultats,
        "total": len(resultats),
        "rayon_km": rayon_km,
    }


def verifier_disponibilite_agent(id_agent: str) -> dict:
    """Verifie si un agent est disponible et a de la flotte."""
    res = obtenir_agent(id_agent)
    if not res["succes"]:
        return res
    agent = res["agent"]
    disponible = (
        agent["statut"] == "en_ligne"
        and agent["solde_flotte_xof"] > 0
        and "suspendu_en_investigation" not in agent["signalements"]
    )
    return {
        "succes": True,
        "id_agent": id_agent,
        "disponible": disponible,
        "statut": agent["statut"],
        "solde_flotte_xof": agent["solde_flotte_xof"],
        "note": agent["note"],
        "signalements": agent["signalements"],
    }


def signaler_agent(id_agent: str, type_signalement: str, id_transaction: str = None) -> dict:
    """Signale un probleme sur un agent au responsable reseau."""
    res = obtenir_agent(id_agent)
    if not res["succes"]:
        return res
    agent = res["agent"]
    return {
        "succes": True,
        "id_agent": id_agent,
        "nom_agent": agent["nom"],
        "type_signalement": type_signalement,
        "id_transaction": id_transaction,
        "statut": "signalement_enregistre",
        "message": "Signalement transmis au responsable reseau agents. Traitement sous 2h.",
        "horodatage": _horodatage(),
    }
