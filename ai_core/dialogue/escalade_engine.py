"""
Moteur d'escalade — 6 regles metier.
Evalue si une conversation doit etre transferee vers un conseiller humain.
Chaque regle a une priorite, une cible et un SLA.
"""
from datetime import datetime, timezone


# ── Definition des regles ──────────────────────────────────────────────────────

REGLES_ESCALADE = [
    {
        "id": "fraude_sim_swap",
        "nom": "Fraude ou SIM swap detecte",
        "priorite": "P1",
        "sla_minutes": 5,
        "cible": "equipe_securite",
        "description": "Transaction avec flag fraude ou SIM swap detecte",
    },
    {
        "id": "montant_eleve",
        "nom": "Transaction a montant eleve",
        "priorite": "P1",
        "sla_minutes": 15,
        "cible": "conseiller_senior_n2",
        "description": "Montant superieur a 500 000 XOF",
        "seuil_xof": 500000,
    },
    {
        "id": "frustration_client",
        "nom": "Client tres frustre",
        "priorite": "P2",
        "sla_minutes": 10,
        "cible": "conseiller_relation_client",
        "description": "Sentiment = frustre detecte par NLU",
    },
    {
        "id": "echec_resolution",
        "nom": "Echec de resolution apres 2 tentatives",
        "priorite": "P2",
        "sla_minutes": 30,
        "cible": "conseiller_n2",
        "description": "L'IA n'a pas pu resoudre apres 2 tours de dialogue",
    },
    {
        "id": "demande_humain",
        "nom": "Client demande un conseiller humain",
        "priorite": "P2",
        "sla_minutes": 5,
        "cible": "conseiller_disponible",
        "description": "Demande explicite de parler a un humain",
    },
    {
        "id": "litige_agent",
        "nom": "Litige avec agent reseau",
        "priorite": "P2",
        "sla_minutes": 120,
        "cible": "responsable_reseau_agents",
        "description": "Agent frauduleux ou depot non credite par agent",
    },
]

MOTS_DEMANDE_HUMAIN = [
    "conseiller", "humain", "agent", "personne", "quelqu'un",
    "operateur", "responsable", "parler a", "mettre en relation",
    "benn nit", "conseiller bi", "defe ma ak",
]

MOTS_LITIGE_AGENT = [
    "agent", "boutique", "point wave", "orange money shop",
    "n'a pas credite", "a pris mon argent", "sans crediter",
    "encaisse", "joxoon", "depot",
]


# ── Evaluateur ─────────────────────────────────────────────────────────────────

class MoteurEscalade:
    """
    Evalue les 6 regles d'escalade sur le contexte courant.
    Retourne la regle declenchee la plus prioritaire ou None.
    """

    def evaluer(
        self,
        message: str,
        analyse_nlu: dict,
        contexte,
        transaction: dict = None,
    ) -> dict | None:
        """
        Evalue toutes les regles dans l'ordre de priorite.
        Retourne la premiere regle declenchee ou None.
        """
        msg_lower = message.lower()
        sentiment = analyse_nlu.get("sentiment", "neutre")
        intention = analyse_nlu.get("intention", {}).get("id", "inconnu")
        entites = analyse_nlu.get("entites", {})
        montant = entites.get("montant_xof")

        # Regle 1 — Fraude / SIM swap
        if self._detecter_fraude(transaction, message):
            return self._construire_resultat("fraude_sim_swap", message)

        # Regle 2 — Montant eleve
        if montant and montant > 500000:
            return self._construire_resultat("montant_eleve", message, {"montant": montant})
        if transaction and transaction.get("montant_xof", 0) > 500000:
            return self._construire_resultat("montant_eleve", message,
                                            {"montant": transaction["montant_xof"]})

        # Regle 3 — Client frustre
        if sentiment == "frustre":
            return self._construire_resultat("frustration_client", message)

        # Regle 5 — Demande explicite humain (avant echec pour respecter le client)
        if self._detecter_demande_humain(msg_lower):
            return self._construire_resultat("demande_humain", message)

        # Regle 6 — Litige agent
        if self._detecter_litige_agent(intention, msg_lower, transaction):
            return self._construire_resultat("litige_agent", message)

        # Regle 4 — Echec resolution apres 2 tentatives
        if hasattr(contexte, 'tentatives_resolution') and contexte.tentatives_resolution >= 2:
            return self._construire_resultat("echec_resolution", message)

        return None

    def _detecter_fraude(self, transaction: dict, message: str) -> bool:
        """Detecte les signaux de fraude dans la transaction ou le message."""
        mots_fraude = [
            "arnaque", "fraude", "vole", "pirate", "sim swap",
            "vide mon compte", "acces non autorise", "escroquerie",
            "quelqu'un utilise", "dama ko jafe", "sama xaalis bi dem",
        ]
        msg_lower = message.lower()
        if any(mot in msg_lower for mot in mots_fraude):
            return True
        if transaction:
            signalements = transaction.get("signalements_fraude", [])
            if any(s in ["sim_swap_suspecte", "fraude_suspectee"] for s in signalements):
                return True
            if transaction.get("motif_echec") in ["fraude_detectee", "sim_swap"]:
                return True
        return False

    def _detecter_demande_humain(self, msg_lower: str) -> bool:
        """Detecte si le client demande explicitement a parler a un humain."""
        return any(mot in msg_lower for mot in MOTS_DEMANDE_HUMAIN)

    def _detecter_litige_agent(
        self, intention: str, msg_lower: str, transaction: dict
    ) -> bool:
        """Detecte un litige avec un agent reseau."""
        if intention == "depot_non_credite":
            return True
        if any(mot in msg_lower for mot in MOTS_LITIGE_AGENT):
            return True
        if transaction:
            litige = transaction.get("litige", {})
            if litige.get("type") in ["fraude_agent", "encaissement_sans_credit"]:
                return True
        return False

    def _construire_resultat(
        self, id_regle: str, message: str, donnees: dict = None
    ) -> dict:
        """Construit le resultat d'escalade avec toutes les infos necessaires."""
        regle = next(r for r in REGLES_ESCALADE if r["id"] == id_regle)
        return {
            "escalade": True,
            "regle": regle,
            "message_declencheur": message,
            "donnees": donnees or {},
            "horodatage": datetime.now(timezone.utc).isoformat(),
        }

    def generer_message_escalade(
        self, resultat: dict, langue: str = "fr", nom_client: str = "Client"
    ) -> str:
        """
        Genere le message a envoyer au client lors d'une escalade.
        Adapte selon la langue et la priorite.
        """
        regle = resultat["regle"]
        sla = regle["sla_minutes"]
        delai = f"{sla} minutes" if sla < 60 else f"{sla // 60} heure(s)"

        if langue == "wo":
            if regle["priorite"] == "P1":
                return (
                    f"Mbaa mu yendoo {nom_client}. Sama probleme bi dafa am solo torop. "
                    f"Dama lay yonnee ci benn conseiller bu xam xam ci kanam. "
                    f"Dinay jooy ci yow ci {delai}."
                )
            return (
                f"{nom_client}, dama lay yonnee ci benn conseiller. "
                f"Dinay jooy ci yow ci {delai}. Jere jef sa patience bi."
            )

        if regle["priorite"] == "P1":
            return (
                f"Je comprends l'urgence de votre situation, {nom_client}. "
                f"Je transfere immediatement votre demande a notre equipe specialisee. "
                f"Un conseiller vous contactera dans moins de {delai}. "
                f"Vos fonds sont en securite."
            )
        return (
            f"{nom_client}, je transfere votre demande a un conseiller humain "
            f"qui pourra mieux vous aider. "
            f"Vous serez contacte(e) dans {delai}. "
            f"Merci de votre patience."
        )