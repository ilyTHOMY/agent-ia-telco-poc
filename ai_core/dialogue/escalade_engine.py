from datetime import datetime, timezone


REGLES_ESCALADE = [
    {
        "id": "fraude_sim_swap",
        "nom": "Fraude ou SIM swap detecte",
        "priorite": "P1",
        "sla_minutes": 5,
        "cible": "equipe_securite",
    },
    {
        "id": "montant_eleve",
        "nom": "Transaction a montant eleve",
        "priorite": "P1",
        "sla_minutes": 15,
        "cible": "conseiller_senior_n2",
        "seuil_xof": 500000,
    },
    {
        "id": "frustration_client",
        "nom": "Client tres frustre",
        "priorite": "P2",
        "sla_minutes": 10,
        "cible": "conseiller_relation_client",
    },
    {
        "id": "echec_resolution",
        "nom": "Echec de resolution apres 2 incomprehensions consecutives",
        "priorite": "P2",
        "sla_minutes": 30,
        "cible": "conseiller_n2",
    },
    {
        "id": "demande_humain",
        "nom": "Client demande explicitement un conseiller humain",
        "priorite": "P2",
        "sla_minutes": 5,
        "cible": "conseiller_disponible",
    },
    {
        "id": "litige_agent",
        "nom": "Litige avec agent reseau",
        "priorite": "P2",
        "sla_minutes": 120,
        "cible": "responsable_reseau_agents",
    },
]

# ── Mots cles tres explicites pour demande humain 
# Ne pas mettre "agent" seul — ca cree une confusion avec "litige agent"
MOTS_DEMANDE_HUMAIN_EXPLICITES = [
    "parler a un conseiller",
    "parler a quelqu'un",
    "je veux un humain",
    "mettre moi en relation",
    "un agent humain",
    "une vraie personne",
    "passer moi quelqu'un",
    "bega naa dem ag benn nit",
    "defe ma ak benn conseiller",
    "conseiller humain",
    "operateur humain",
]

# ── Mots cles litige agent reseau (distincte de "agent humain") 
MOTS_LITIGE_AGENT = [
    "agent a pris",
    "agent n'a pas credite",
    "agent a encaisse",
    "sans crediter",
    "boutique",
    "point wave",
    "point orange",
    "depot non credite",
    "l'agent a refuse",
    "agent frauduleux",
    "agent bi jox",
    "agent bi dafa",
    "joxoon ma xaalis",
]

# ── Mots cles fraude ───────────────────────────────────────────────────────
MOTS_FRAUDE = [
    "arnaque", "fraude", "vole", "pirate", "sim swap",
    "vide mon compte", "acces non autorise", "escroquerie",
    "quelqu'un utilise mon compte", "transactions inconnues",
    "dama ko jafe jafe", "ku nekk am sama compte",
]

# ── Intentions financieres (pour filtrer montant eleve) ───────────────────
INTENTIONS_FINANCIERES = {
    "transaction_non_recue", "retrait_echoue", "depot_non_credite",
    "double_debit", "mauvais_beneficiaire", "fraude_suspectee",
}


class MoteurEscalade:

    def evaluer(
        self,
        message: str,
        analyse_nlu: dict,
        contexte,
        transaction: dict = None,
    ) -> dict | None:
        msg = message.lower()
        sentiment = analyse_nlu.get("sentiment", "neutre")
        intention_id = analyse_nlu.get("intention", {}).get("id", "inconnu")
        montant = analyse_nlu.get("entites", {}).get("montant_xof")

        # ── Regle 1 : Fraude / SIM swap 
        if self._detecter_fraude(msg, transaction):
            return self._resultat("fraude_sim_swap", message)

        # ── Regle 2 : Montant eleve SEULEMENT si intention financiere 
        if montant and montant > 500000 and intention_id in INTENTIONS_FINANCIERES:
            return self._resultat("montant_eleve", message, {"montant": montant})
        if transaction and transaction.get("montant_xof", 0) > 500000:
            if intention_id in INTENTIONS_FINANCIERES:
                return self._resultat("montant_eleve", message,
                                      {"montant": transaction["montant_xof"]})

        # ── Regle 6 : Litige agent — AVANT demande humain pour eviter confusion
        if self._detecter_litige_agent(intention_id, msg, transaction):
            return self._resultat("litige_agent", message)

        # ── Regle 3 : Frustration 
        if sentiment == "frustre":
            return self._resultat("frustration_client", message)

        # ── Regle 5 : Demande humain EXPLICITE 
        if self._detecter_demande_humain_explicite(msg):
            return self._resultat("demande_humain", message)

        # ── Regle 4 : Echec resolution — 2 incomprehensions consecutives ──
        # On verifie que c'est bien une incomprehension et pas juste 2 messages
        nb_incomprehensions = getattr(contexte, 'incomprehensions_consecutives', 0)
        if nb_incomprehensions >= 2:
            return self._resultat("echec_resolution", message)

        return None

    def _detecter_fraude(self, msg: str, transaction: dict) -> bool:
        if any(mot in msg for mot in MOTS_FRAUDE):
            return True
        if transaction:
            signalements = transaction.get("signalements_fraude", [])
            if any(s in ["sim_swap_suspecte", "fraude_suspectee"] for s in signalements):
                return True
        return False

    def _detecter_litige_agent(
        self, intention: str, msg: str, transaction: dict
    ) -> bool:
        # Intention directe
        if intention == "depot_non_credite":
            return True
        # Mots cles specifiques litige agent reseau
        if any(mot in msg for mot in MOTS_LITIGE_AGENT):
            return True
        # Transaction avec litige agent
        if transaction:
            litige = transaction.get("litige", {})
            if litige.get("type") in ["fraude_agent", "encaissement_sans_credit"]:
                return True
        return False

    def _detecter_demande_humain_explicite(self, msg: str) -> bool:
        """Uniquement si le client demande EXPLICITEMENT un humain."""
        return any(mot in msg for mot in MOTS_DEMANDE_HUMAIN_EXPLICITES)

    def _resultat(self, id_regle: str, message: str, donnees: dict = None) -> dict:
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
        regle = resultat["regle"]
        sla = regle["sla_minutes"]
        delai = f"{sla} minutes" if sla < 60 else f"{sla // 60} heure(s)"

        if langue == "wo":
            if regle["priorite"] == "P1":
                return (
                    f"Mbaa mu yendoo {nom_client}. Sama probleme bi dafa am solo torop. "
                    f"Dama lay yonnee ci benn conseiller bu xam xam. "
                    f"Dinay jooy ci yow ci {delai}."
                )
            return (
                f"{nom_client}, dama lay yonnee ci benn conseiller. "
                f"Dinay jooy ci yow ci {delai}. Jere jef sa patience bi."
            )

        if regle["priorite"] == "P1":
            return (
                f"Je comprends l'urgence, {nom_client}. "
                f"Je transfere votre demande a notre equipe specialisee immediatement. "
                f"Un conseiller vous contactera dans moins de {delai}."
            )
        return (
            f"{nom_client}, je transfere votre demande a un conseiller "
            f"qui pourra mieux vous aider. "
            f"Vous serez contacte(e) dans {delai}."
        )