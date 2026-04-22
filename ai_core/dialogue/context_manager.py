"""
Gestionnaire de contexte conversationnel.
Maintient l'historique de la conversation, le profil client charge,
et l'etat courant de la session dans Redis.
"""
import json
from datetime import datetime, timezone
from typing import Optional

MAX_HISTORIQUE = 20  # nb max de messages gardes en contexte


class ContexteConversation:
    """
    Represente le contexte complet d'une conversation client.
    Instancie une fois par session WebSocket et persiste dans Redis.
    """

    def __init__(self, id_session: str, telephone: str, canal: str = "chat"):
        self.id_session = id_session
        self.telephone = telephone
        self.canal = canal
        self.date_debut = datetime.now(timezone.utc).isoformat()

        # Profil client charge depuis mock API apres auth
        self.client: Optional[dict] = None
        self.authentifie: bool = False
        self.tentatives_pin: int = 0

        # Historique des messages (format LangChain)
        self.historique: list[dict] = []

        # Etat du dialogue
        self.intention_courante: Optional[str] = None
        self.entites_courantes: dict = {}
        self.sentiment_courant: str = "neutre"
        self.langue: str = "fr"

        # Suivi des tentatives de resolution
        self.tentatives_resolution: int = 0
        self.tickets_crees: list[str] = []
        self.escalade_effectuee: bool = False

        # Donnees de la reclamation en cours
        self.transaction_courante: Optional[dict] = None

    def ajouter_message(self, role: str, contenu: str) -> None:
        """Ajoute un message a l'historique (role: 'human' ou 'assistant')."""
        self.historique.append({
            "role": role,
            "contenu": contenu,
            "horodatage": datetime.now(timezone.utc).isoformat(),
        })
        # Garder seulement les N derniers messages
        if len(self.historique) > MAX_HISTORIQUE:
            self.historique = self.historique[-MAX_HISTORIQUE:]

    def formater_historique_prompt(self) -> str:
        """Formate l'historique pour injection dans le prompt Gemini."""
        if not self.historique:
            return ""
        lignes = []
        for msg in self.historique[-10:]:  # 10 derniers messages
            role = "Client" if msg["role"] == "human" else "Agent IA"
            lignes.append(f"{role}: {msg['contenu']}")
        return "\n".join(lignes)

    def formater_contexte_client(self) -> str:
        """Formate le profil client pour injection dans le prompt Gemini."""
        if not self.client:
            return "Client non authentifie."
        c = self.client
        return (
            f"Operateur : {c.get('operateur', 'inconnu').replace('_', ' ').title()}\n"
            f"Nom : {c.get('nom', 'Client')}\n"
            f"Segment : {c.get('segment', 'standard')}\n"
            f"Statut compte : {c.get('statut_compte', 'inconnu')}\n"
            f"Statut KYC : {c.get('statut_kyc', 'inconnu')}\n"
            f"Solde : {c.get('solde_xof', 0):,} XOF\n"
            f"Plafond journalier : {c.get('plafond_journalier_xof', 0):,} XOF\n"
            f"Langue preferee : {c.get('langue', 'fr')}"
        )

    def incrementer_tentatives(self) -> None:
        self.tentatives_resolution += 1

    def to_dict(self) -> dict:
        """Serialise le contexte pour stockage Redis."""
        return {
            "id_session": self.id_session,
            "telephone": self.telephone,
            "canal": self.canal,
            "date_debut": self.date_debut,
            "client": self.client,
            "authentifie": self.authentifie,
            "tentatives_pin": self.tentatives_pin,
            "historique": self.historique,
            "intention_courante": self.intention_courante,
            "entites_courantes": self.entites_courantes,
            "sentiment_courant": self.sentiment_courant,
            "langue": self.langue,
            "tentatives_resolution": self.tentatives_resolution,
            "tickets_crees": self.tickets_crees,
            "escalade_effectuee": self.escalade_effectuee,
            "transaction_courante": self.transaction_courante,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContexteConversation":
        """Reconstruit un contexte depuis Redis."""
        ctx = cls(data["id_session"], data["telephone"], data.get("canal", "chat"))
        ctx.date_debut = data.get("date_debut", ctx.date_debut)
        ctx.client = data.get("client")
        ctx.authentifie = data.get("authentifie", False)
        ctx.tentatives_pin = data.get("tentatives_pin", 0)
        ctx.historique = data.get("historique", [])
        ctx.intention_courante = data.get("intention_courante")
        ctx.entites_courantes = data.get("entites_courantes", {})
        ctx.sentiment_courant = data.get("sentiment_courant", "neutre")
        ctx.langue = data.get("langue", "fr")
        ctx.tentatives_resolution = data.get("tentatives_resolution", 0)
        ctx.tickets_crees = data.get("tickets_crees", [])
        ctx.escalade_effectuee = data.get("escalade_effectuee", False)
        ctx.transaction_courante = data.get("transaction_courante")
        return ctx


class GestionnaireContexte:
    """
    Interface Redis pour persister et recuperer les contextes de conversation.
    Utilise Redis comme store de sessions.
    """

    TTL_SESSION = 3600  # 1 heure d'inactivite avant expiration

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._cache_local: dict[str, ContexteConversation] = {}

    def _cle(self, id_session: str) -> str:
        return f"session:{id_session}"

    async def creer(self, id_session: str, telephone: str, canal: str = "chat") -> ContexteConversation:
        """Cree un nouveau contexte de conversation."""
        ctx = ContexteConversation(id_session, telephone, canal)
        await self.sauvegarder(ctx)
        return ctx

    async def obtenir(self, id_session: str) -> Optional[ContexteConversation]:
        """Recupere un contexte depuis Redis ou le cache local."""
        # Cache local d'abord
        if id_session in self._cache_local:
            return self._cache_local[id_session]
        # Redis
        if self._redis:
            try:
                data = await self._redis.get(self._cle(id_session))
                if data:
                    ctx = ContexteConversation.from_dict(json.loads(data))
                    self._cache_local[id_session] = ctx
                    return ctx
            except Exception as e:
                print(f"[CONTEXTE] Erreur Redis get : {e}")
        return None

    async def sauvegarder(self, ctx: ContexteConversation) -> None:
        """Persiste le contexte dans Redis."""
        self._cache_local[ctx.id_session] = ctx
        if self._redis:
            try:
                await self._redis.setex(
                    self._cle(ctx.id_session),
                    self.TTL_SESSION,
                    json.dumps(ctx.to_dict(), ensure_ascii=False),
                )
            except Exception as e:
                print(f"[CONTEXTE] Erreur Redis set : {e}")

    async def supprimer(self, id_session: str) -> None:
        """Supprime une session (deconnexion client)."""
        self._cache_local.pop(id_session, None)
        if self._redis:
            try:
                await self._redis.delete(self._cle(id_session))
            except Exception as e:
                print(f"[CONTEXTE] Erreur Redis delete : {e}")

    def lister_sessions_actives(self) -> list[str]:
        """Retourne les sessions actives en cache local."""
        return list(self._cache_local.keys())