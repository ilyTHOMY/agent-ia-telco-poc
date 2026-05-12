"""
Mock API Reseau Agents v3 — recherche par quartier/ville
sans coordonnees GPS. L'IA demande le quartier au client
et on filtre par localisation.quartier (comparaison insensible a la casse).
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


def _agent_disponible(agent: dict) -> bool:
    return (
        agent.get("statut") == "en_ligne"
        and agent.get("solde_flotte_xof", 0) > 0
        and "suspendu_en_investigation" not in agent.get("signalements", [])
    )


def lister_agents_par_quartier(
    quartier: str,
    operateur: str = None,
) -> dict:
    """
    Cherche les agents dans un quartier specifique.
    Comparaison insensible a la casse et aux accents basiques.
    """
    q = quartier.lower().strip()
    resultats = []

    for agent in _charger_agents():
        if not _agent_disponible(agent):
            continue
        if operateur and agent.get("operateur") != operateur:
            continue

        loc = agent.get("localisation", {})
        quartier_agent = loc.get("quartier", "").lower()
        ville_agent    = loc.get("ville", "").lower()

        # Match sur quartier ou ville
        if q in quartier_agent or q in ville_agent or quartier_agent in q:
            resultats.append(agent)

    resultats.sort(key=lambda a: a.get("note", 0), reverse=True)

    # Lister tous les quartiers connus si aucun resultat
    if not resultats:
        quartiers_connus = list({
            a.get("localisation", {}).get("quartier", "")
            for a in _charger_agents()
            if _agent_disponible(a) and (not operateur or a.get("operateur") == operateur)
        })
        quartiers_connus = [q for q in quartiers_connus if q]
        return {
            "succes": True,
            "agents": [],
            "total": 0,
            "quartier_recherche": quartier,
            "quartiers_disponibles": quartiers_connus,
            "message": f"Aucun agent disponible a {quartier}.",
        }

    return {
        "succes": True,
        "agents": resultats,
        "total": len(resultats),
        "quartier_recherche": quartier,
    }


def lister_agents_disponibles(operateur: str = None) -> dict:
    """Retourne tous les agents disponibles tries par note."""
    resultats = [
        a for a in _charger_agents()
        if _agent_disponible(a) and (not operateur or a.get("operateur") == operateur)
    ]
    resultats.sort(key=lambda a: a.get("note", 0), reverse=True)
    return {"succes": True, "agents": resultats, "total": len(resultats)}


def obtenir_agent(id_agent: str) -> dict:
    for agent in _charger_agents():
        if agent["id"] == id_agent:
            return {"succes": True, "agent": agent}
    return {"succes": False, "erreur": "Agent introuvable"}


def verifier_disponibilite_agent(id_agent: str) -> dict:
    res = obtenir_agent(id_agent)
    if not res["succes"]:
        return res
    agent = res["agent"]
    return {
        "succes": True,
        "id_agent": id_agent,
        "disponible": _agent_disponible(agent),
        "statut": agent.get("statut"),
        "solde_flotte_xof": agent.get("solde_flotte_xof", 0),
        "note": agent.get("note", 0),
    }


def signaler_agent(id_agent: str, type_signalement: str, id_transaction: str = None) -> dict:
    res = obtenir_agent(id_agent)
    if not res["succes"]:
        return res
    return {
        "succes": True,
        "id_agent": id_agent,
        "type_signalement": type_signalement,
        "statut": "signalement_enregistre",
        "message": "Signalement transmis au responsable reseau. Traitement sous 2h.",
        "horodatage": _horodatage(),
    }
