from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ClientBase(BaseModel):
    telephone: str = Field(..., pattern=r'^\+?[0-9]{10,15}$')
    operateur: Optional[str] = None
    nom: Optional[str] = None
    langue: Optional[str] = "fr"
    statut_compte: Optional[str] = "actif"
    statut_kyc: Optional[str] = "incomplet"
    segment: Optional[str] = "regulier"
    solde_xof: Optional[int] = 0


class ClientConnecte(BaseModel):
    nom: str
    operateur: str
    segment: str
    langue: str


class DemandeAuth(BaseModel):
    telephone: str
    pin: str = Field(..., min_length=4, max_length=4)


class ReponseAuth(BaseModel):
    succes: bool
    message: str
    client: Optional[ClientConnecte] = None
    bloque: Optional[bool] = False
    tentatives_restantes: Optional[int] = None


class TicketCreate(BaseModel):
    telephone: str
    type_reclamation: str
    description: str
    priorite: str = "P3"
    canal: str = "chat"
    id_transaction: Optional[str] = None


class TicketResponse(BaseModel):
    id: str
    telephone: str
    type_reclamation: str
    description: str
    priorite: str
    statut: str
    canal_origine: str
    date_ouverture: str
    sla_heures: int
    agent_assigne: Optional[str] = None


class MessageChat(BaseModel):
    id_session: str
    telephone: str
    message: str
    canal: str = "chat"


class ReponseChat(BaseModel):
    reponse: str
    intention: Optional[str] = None
    sentiment: Optional[str] = None
    langue: Optional[str] = None
    escalade: bool = False
    priorite: Optional[str] = None
    id_ticket: Optional[str] = None
    tickets: list[str] = []


class MetriquesKPI(BaseModel):
    total_tickets: int
    tickets_ouverts: int
    tickets_resolus: int
    tickets_en_cours: int
    incidents_p1: int
    incidents_p2: int
    taux_resolution_pct: float
    sessions_actives: int
