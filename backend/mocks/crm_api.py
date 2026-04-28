"""
Mock CRM v2 — tickets persistes automatiquement dans data/tickets.json.
Plus de perte de donnees au redemarrage Docker.
"""
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

DONNEES_DIR = Path(__file__).parent.parent.parent / "data"
TICKETS_FILE = DONNEES_DIR / "tickets.json"


def _horodatage() -> str:
    return datetime.now(timezone.utc).isoformat()


def _charger_tickets() -> list:
    try:
        with open(TICKETS_FILE, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else data.get("tickets", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _sauvegarder_tickets(tickets: list) -> None:
    with open(TICKETS_FILE, "w", encoding="utf-8") as f:
        json.dump({"tickets": tickets}, f, ensure_ascii=False, indent=2)


def creer_ticket(
    telephone: str,
    type_reclamation: str,
    description: str,
    priorite: str = "P3",
    canal: str = "chat",
    id_transaction: str = None,
    id_client: str = None,
) -> dict:
    """Cree un ticket et le persiste dans tickets.json."""
    if priorite not in {"P1", "P2", "P3", "P4"}:
        priorite = "P3"

    suffixe = telephone[4:7] if len(telephone) >= 7 else "XXX"
    tickets = _charger_tickets()
    id_ticket = f"INC-{suffixe}-2026-{str(len(tickets)+1).zfill(5)}"

    sla_map = {"P1": 1, "P2": 4, "P3": 24, "P4": 72}

    ticket = {
        "id": id_ticket,
        "id_client": id_client or telephone,
        "telephone": telephone,
        "type_reclamation": type_reclamation,
        "description": description,
        "priorite": priorite,
        "statut": "ouvert",
        "canal_origine": canal,
        "id_transaction": id_transaction,
        "date_ouverture": _horodatage(),
        "date_mise_a_jour": _horodatage(),
        "date_cloture": None,
        "agent_assigne": None,
        "sla_heures": sla_map.get(priorite, 24),
        "csat": None,
        "historique": [{
            "action": "ticket_cree",
            "auteur": "agent_ia",
            "date": _horodatage(),
            "note": "Ticket cree automatiquement par l'agent IA.",
        }],
    }

    tickets.append(ticket)
    _sauvegarder_tickets(tickets)
    return {"succes": True, "ticket": ticket}


def obtenir_ticket(id_ticket: str) -> dict:
    tickets = _charger_tickets()
    t = next((t for t in tickets if t["id"] == id_ticket), None)
    if not t:
        return {"succes": False, "erreur": "Ticket introuvable"}
    return {"succes": True, "ticket": t}


def mettre_a_jour_ticket(
    id_ticket: str,
    statut: str = None,
    note: str = None,
    agent_assigne: str = None,
) -> dict:
    tickets = _charger_tickets()
    for t in tickets:
        if t["id"] == id_ticket:
            if statut:
                t["statut"] = statut
                if statut == "resolu":
                    t["date_cloture"] = _horodatage()
            if agent_assigne:
                t["agent_assigne"] = agent_assigne
            t["date_mise_a_jour"] = _horodatage()
            if note:
                t["historique"].append({
                    "action": "mise_a_jour",
                    "auteur": agent_assigne or "agent_ia",
                    "date": _horodatage(),
                    "note": note,
                })
            _sauvegarder_tickets(tickets)
            return {"succes": True, "ticket": t}
    return {"succes": False, "erreur": "Ticket introuvable"}


def enregistrer_csat(id_ticket: str, note_etoiles: int, commentaire: str = "") -> dict:
    """Enregistre la note CSAT (1-5 etoiles) a la fin de la conversation."""
    if not 1 <= note_etoiles <= 5:
        return {"succes": False, "erreur": "Note CSAT invalide (1-5)"}
    tickets = _charger_tickets()
    for t in tickets:
        if t["id"] == id_ticket:
            t["csat"] = {
                "note": note_etoiles,
                "commentaire": commentaire,
                "date": _horodatage(),
            }
            t["historique"].append({
                "action": "csat_recu",
                "auteur": "client",
                "date": _horodatage(),
                "note": f"Note CSAT : {note_etoiles}/5. {commentaire}",
            })
            _sauvegarder_tickets(tickets)
            return {"succes": True, "ticket": t}
    return {"succes": False, "erreur": "Ticket introuvable"}


def lister_tickets_client(telephone: str) -> dict:
    tickets = [t for t in _charger_tickets() if t["telephone"] == telephone]
    tickets.sort(key=lambda t: t["date_ouverture"], reverse=True)
    return {"succes": True, "telephone": telephone, "tickets": tickets, "total": len(tickets)}


def lister_tous_tickets(statut: str = None) -> dict:
    tickets = _charger_tickets()
    if statut:
        tickets = [t for t in tickets if t["statut"] == statut]
    tickets.sort(key=lambda t: t["date_ouverture"], reverse=True)
    return {"succes": True, "tickets": tickets, "total": len(tickets)}


def obtenir_stats_csat() -> dict:
    """Calcule les statistiques CSAT pour le dashboard."""
    tickets = _charger_tickets()
    notes = [t["csat"]["note"] for t in tickets if t.get("csat")]
    if not notes:
        return {"total_evaluations": 0, "moyenne": 0, "repartition": {}}
    repartition = {str(i): notes.count(i) for i in range(1, 6)}
    return {
        "total_evaluations": len(notes),
        "moyenne": round(sum(notes) / len(notes), 2),
        "repartition": repartition,
    }
