"""
Mock API CRM / Ticketing — gestion des tickets de reclamation.
En production : integration Zendesk, Freshdesk ou solution proprietaire.
Les tickets sont stockes en memoire pour le PoC,
puis persistes en PostgreSQL via le module db/.
"""
import uuid
from datetime import datetime, timezone

_tickets: dict = {}


def _horodatage() -> str:
    return datetime.now(timezone.utc).isoformat()


def creer_ticket(
    telephone: str,
    type_reclamation: str,
    description: str,
    priorite: str = "P3",
    canal: str = "chat",
    id_transaction: str = None,
    id_client: str = None,
) -> dict:
    """Cree un nouveau ticket de reclamation."""
    PRIORITES = {"P1", "P2", "P3", "P4"}
    if priorite not in PRIORITES:
        priorite = "P3"

    suffixe = telephone[4:7].upper() if len(telephone) >= 7 else "XXX"
    id_ticket = f"INC-{suffixe}-2026-{str(len(_tickets) + 1).zfill(5)}"

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
        "historique": [
            {
                "action": "ticket_cree",
                "auteur": "agent_ia",
                "date": _horodatage(),
                "note": "Ticket cree automatiquement par l'agent IA.",
            }
        ],
    }
    _tickets[id_ticket] = ticket
    return {"succes": True, "ticket": ticket}


def obtenir_ticket(id_ticket: str) -> dict:
    """Retourne les details d'un ticket."""
    ticket = _tickets.get(id_ticket)
    if not ticket:
        return {"succes": False, "erreur": "Ticket introuvable"}
    return {"succes": True, "ticket": ticket}


def mettre_a_jour_ticket(
    id_ticket: str,
    statut: str = None,
    note: str = None,
    agent_assigne: str = None,
) -> dict:
    """Met a jour le statut ou ajoute une note."""
    ticket = _tickets.get(id_ticket)
    if not ticket:
        return {"succes": False, "erreur": "Ticket introuvable"}
    if statut:
        ticket["statut"] = statut
        if statut == "resolu":
            ticket["date_cloture"] = _horodatage()
    if agent_assigne:
        ticket["agent_assigne"] = agent_assigne
    ticket["date_mise_a_jour"] = _horodatage()
    if note:
        ticket["historique"].append({
            "action": "mise_a_jour",
            "auteur": agent_assigne or "agent_ia",
            "date": _horodatage(),
            "note": note,
        })
    return {"succes": True, "ticket": ticket}


def lister_tickets_client(telephone: str) -> dict:
    """Retourne tous les tickets d'un client."""
    tickets = [t for t in _tickets.values() if t["telephone"] == telephone]
    tickets.sort(key=lambda t: t["date_ouverture"], reverse=True)
    return {"succes": True, "telephone": telephone, "tickets": tickets, "total": len(tickets)}


def lister_tous_tickets(statut: str = None) -> dict:
    """Retourne tous les tickets (pour le dashboard operateur)."""
    tickets = list(_tickets.values())
    if statut:
        tickets = [t for t in tickets if t["statut"] == statut]
    tickets.sort(key=lambda t: t["date_ouverture"], reverse=True)
    return {"succes": True, "tickets": tickets, "total": len(tickets)}
