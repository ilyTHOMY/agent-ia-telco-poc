"""
CRUD PostgreSQL — operations sur les tables via SQLAlchemy async.
"""
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.schemas import Ticket, MessageConversation, Session as SessionModel


# ── Tickets ────────────────────────────────────────────────────────────────────

async def creer_ticket_db(db: AsyncSession, data: dict) -> Ticket:
    ticket = Ticket(**data)
    db.add(ticket)
    await db.flush()
    return ticket


async def obtenir_ticket_db(db: AsyncSession, id_ticket: str) -> Ticket | None:
    res = await db.execute(select(Ticket).where(Ticket.id == id_ticket))
    return res.scalar_one_or_none()


async def lister_tickets_db(
    db: AsyncSession,
    statut: str = None,
    priorite: str = None,
    limite: int = 50
) -> list[Ticket]:
    q = select(Ticket).order_by(Ticket.date_ouverture.desc()).limit(limite)
    if statut:
        q = q.where(Ticket.statut == statut)
    if priorite:
        q = q.where(Ticket.priorite == priorite)
    res = await db.execute(q)
    return list(res.scalars().all())


async def mettre_a_jour_ticket_db(
    db: AsyncSession,
    id_ticket: str,
    statut: str = None,
    agent_assigne: str = None,
) -> Ticket | None:
    ticket = await obtenir_ticket_db(db, id_ticket)
    if not ticket:
        return None
    if statut:
        ticket.statut = statut
        if statut == "resolu":
            ticket.date_cloture = datetime.now(timezone.utc)
    if agent_assigne:
        ticket.agent_assigne = agent_assigne
    ticket.date_mise_a_jour = datetime.now(timezone.utc)
    await db.flush()
    return ticket


# ── Conversations ──────────────────────────────────────────────────────────────

async def sauvegarder_message_db(db: AsyncSession, data: dict) -> MessageConversation:
    msg = MessageConversation(**data)
    db.add(msg)
    await db.flush()
    return msg


async def obtenir_historique_db(
    db: AsyncSession,
    id_session: str,
    limite: int = 20
) -> list[MessageConversation]:
    q = (select(MessageConversation)
         .where(MessageConversation.id_session == id_session)
         .order_by(MessageConversation.horodatage.desc())
         .limit(limite))
    res = await db.execute(q)
    return list(reversed(res.scalars().all()))


# ── Sessions ───────────────────────────────────────────────────────────────────

async def creer_ou_maj_session_db(db: AsyncSession, data: dict) -> SessionModel:
    existing = await db.execute(
        select(SessionModel).where(SessionModel.id_session == data["id_session"])
    )
    session = existing.scalar_one_or_none()
    if session:
        for k, v in data.items():
            setattr(session, k, v)
        session.date_derniere_activite = datetime.now(timezone.utc)
    else:
        session = SessionModel(**data)
        db.add(session)
    await db.flush()
    return session


async def lister_sessions_actives_db(db: AsyncSession) -> list[SessionModel]:
    q = select(SessionModel).where(SessionModel.authentifie == True)
    res = await db.execute(q)
    return list(res.scalars().all())
