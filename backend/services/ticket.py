"""
Service ticket — synchronise le mock CRM (memoire) et PostgreSQL.
"""
from datetime import datetime, timezone
from backend.mocks.crm_api import (
    creer_ticket as creer_ticket_mock,
    mettre_a_jour_ticket as maj_ticket_mock,
    obtenir_ticket as obtenir_ticket_mock,
)


async def creer_ticket_complet(
    db,
    telephone: str,
    type_reclamation: str,
    description: str,
    priorite: str = "P3",
    canal: str = "chat",
    id_transaction: str = None,
    id_client: str = None,
) -> dict:
    """
    Cree un ticket dans le mock CRM ET dans PostgreSQL.
    Le mock CRM est la source principale (PoC).
    PostgreSQL sert a la persistance longue duree.
    """
    # 1. Creer dans le mock (source de verite PoC)
    res = creer_ticket_mock(
        telephone=telephone,
        type_reclamation=type_reclamation,
        description=description,
        priorite=priorite,
        canal=canal,
        id_transaction=id_transaction,
        id_client=id_client,
    )

    if not res["succes"]:
        return res

    ticket = res["ticket"]

    # 2. Persister en PostgreSQL si disponible
    if db is not None:
        try:
            from backend.db.crud import creer_ticket_db
            await creer_ticket_db(db, {
                "id": ticket["id"],
                "id_client": id_client or telephone,
                "telephone": telephone,
                "type_reclamation": type_reclamation,
                "description": description,
                "priorite": priorite,
                "statut": "ouvert",
                "canal_origine": canal,
                "id_transaction": id_transaction,
                "sla_heures": ticket.get("sla_heures", 24),
            })
        except Exception as e:
            print(f"[TICKET] Erreur PostgreSQL (non bloquant) : {e}")

    return res


async def fermer_ticket(db, id_ticket: str) -> dict:
    """Ferme un ticket dans le mock et PostgreSQL."""
    res = maj_ticket_mock(id_ticket, statut="resolu", note="Ticket ferme par l'agent IA.")
    if db and res["succes"]:
        try:
            from backend.db.crud import mettre_a_jour_ticket_db
            await mettre_a_jour_ticket_db(db, id_ticket, statut="resolu")
        except Exception as e:
            print(f"[TICKET] Erreur fermeture PostgreSQL : {e}")
    return res
