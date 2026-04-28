"""
Mock API Reseau Agents v2 — adapte a la nouvelle structure agents.json
sans coordonnees GPS (champ localisation simplifie).
"""
import json
from pathlib import Path
from datetime import datetime, timezone

DONNEES_DIR = Path(__file__).parent.parent.parent / "data"


def _charger_agents() -> list:
    with open(DONNEES_DIR / "agents.json", encoding="utf-8") as f:
        data = json.load(f)
        return data if isinstance(data, list) else data.get("agents", [])


def _horodatage() -> str:
    return datetime.now(timezone.utc).isoformat()


def obtenir_agent(id_agent: str) -> dict:
    """Retourne les details d'un agent par son ID."""
    for agent in _charger_agents():
        if agent["id"] == id_agent:
            return {"succes": True, "agent": agent}
    return {"succes": False, "erreur": "Agent introuvable"}


def lister_agents_disponibles(operateur: str = None, ville: str = None) -> dict:
    """
    Retourne les agents en ligne avec de la flotte.
    Filtre optionnel par operateur et ville.
    Sans GPS — tri par note decroissante.
    """
    resultats = []
    for agent in _charger_agents():
        if agent.get("statut") != "en_ligne":
            continue
        if agent.get("solde_flotte_xof", 0) <= 0:
            continue
        if "suspendu_en_investigation" in agent.get("signalements", []):
            continue
        if operateur and agent.get("operateur") != operateur:
            continue
        loc = agent.get("localisation", {})
        if ville and loc.get("ville", "").lower() != ville.lower():
            continue
        resultats.append(agent)

    resultats.sort(key=lambda a: a.get("note", 0), reverse=True)
    return {
        "succes": True,
        "agents": resultats,
        "total": len(resultats),
    }


def lister_agents_proches(
    latitude: float = None,
    longitude: float = None,
    operateur: str = None,
    rayon_km: float = 5.0,
) -> dict:
    """
    Compatibilite avec l'orchestrateur — appelle lister_agents_disponibles
    si pas de GPS disponible dans les donnees agents.
    """
    return lister_agents_disponibles(operateur=operateur)


def verifier_disponibilite_agent(id_agent: str) -> dict:
    """Verifie si un agent est disponible et a de la flotte."""
    res = obtenir_agent(id_agent)
    if not res["succes"]:
        return res
    agent = res["agent"]
    disponible = (
        agent.get("statut") == "en_ligne"
        and agent.get("solde_flotte_xof", 0) > 0
        and "suspendu_en_investigation" not in agent.get("signalements", [])
    )
    return {
        "succes": True,
        "id_agent": id_agent,
        "disponible": disponible,
        "statut": agent.get("statut"),
        "solde_flotte_xof": agent.get("solde_flotte_xof", 0),
        "note": agent.get("note", 0),
        "signalements": agent.get("signalements", []),
    }


def signaler_agent(id_agent: str, type_signalement: str, id_transaction: str = None) -> dict:
    """Signale un probleme sur un agent."""
    res = obtenir_agent(id_agent)
    if not res["succes"]:
        return res
    agent = res["agent"]
    return {
        "succes": True,
        "id_agent": id_agent,
        "nom_agent": agent.get("nom"),
        "type_signalement": type_signalement,
        "id_transaction": id_transaction,
        "statut": "signalement_enregistre",
        "message": "Signalement transmis au responsable reseau agents. Traitement sous 2h.",
        "horodatage": _horodatage(),
    }
