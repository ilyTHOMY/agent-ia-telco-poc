"""
Modeles SQLAlchemy — tables PostgreSQL.
Correspond exactement aux tables creees dans init_services.sh.
"""
from datetime import datetime, timezone
from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.db.database import Base


def _now():
    return datetime.now(timezone.utc)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    id_client: Mapped[str | None] = mapped_column(String(50))
    telephone: Mapped[str] = mapped_column(String(20), index=True)
    type_reclamation: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    priorite: Mapped[str] = mapped_column(String(5), default="P3", index=True)
    statut: Mapped[str] = mapped_column(String(30), default="ouvert", index=True)
    canal_origine: Mapped[str | None] = mapped_column(String(30))
    id_transaction: Mapped[str | None] = mapped_column(String(100))
    date_ouverture: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    date_mise_a_jour: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    date_cloture: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    agent_assigne: Mapped[str | None] = mapped_column(String(100))
    sla_heures: Mapped[int] = mapped_column(Integer, default=24)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "id_client": self.id_client,
            "telephone": self.telephone,
            "type_reclamation": self.type_reclamation,
            "description": self.description,
            "priorite": self.priorite,
            "statut": self.statut,
            "canal_origine": self.canal_origine,
            "id_transaction": self.id_transaction,
            "date_ouverture": self.date_ouverture.isoformat() if self.date_ouverture else None,
            "date_cloture": self.date_cloture.isoformat() if self.date_cloture else None,
            "agent_assigne": self.agent_assigne,
            "sla_heures": self.sla_heures,
        }


class MessageConversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_session: Mapped[str] = mapped_column(String(100), index=True)
    telephone: Mapped[str] = mapped_column(String(20))
    canal: Mapped[str] = mapped_column(String(30), default="chat")
    role: Mapped[str] = mapped_column(String(20))
    contenu: Mapped[str] = mapped_column(Text)
    intention: Mapped[str | None] = mapped_column(String(100))
    sentiment: Mapped[str | None] = mapped_column(String(30))
    langue: Mapped[str | None] = mapped_column(String(10))
    horodatage: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Session(Base):
    __tablename__ = "sessions"

    id_session: Mapped[str] = mapped_column(String(100), primary_key=True)
    telephone: Mapped[str] = mapped_column(String(20), index=True)
    canal: Mapped[str | None] = mapped_column(String(30))
    authentifie: Mapped[bool] = mapped_column(Boolean, default=False)
    langue: Mapped[str] = mapped_column(String(10), default="fr")
    escalade_effectuee: Mapped[bool] = mapped_column(Boolean, default=False)
    date_debut: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    date_derniere_activite: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
