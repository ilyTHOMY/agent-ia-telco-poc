"""
Moteur d'escalade v2 — corrections :
1. Escalade echec_resolution : uniquement si le CLIENT signale que ca n'a pas marche
   (pas un compteur automatique apres N messages)
2. Demande humain : uniquement si explicite, pas si "agent" apparait dans un contexte de litige
3. Litige agent : detection separee et correcte
"""
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
        "nom": "Client signale que l'IA n'a pas resolu son probleme",
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

# ── Mots cles fraude ───────────────────────────────────────────────────────────
MOTS_FRAUDE = [
    "arnaque", "fraude", "vole", "pirate", "sim swap",
    "vide mon compte", "acces non autorise", "escroquerie",
    "quelqu'un utilise", "dama ko jafe", "sama xaalis bi dem",
    "ku nekk am sama compte",
]

# ── Demande humain EXPLICITE uniquement ───────────────────────────────────────
# Mots qui signifient vraiment "je veux parler a un humain"
# Ne pas inclure "agent" seul car ca peut etre "agent reseau"
MOTS_DEMANDE_HUMAIN_EXPLICITE = [
    "parler a un conseiller",
    "parler a quelqu'un",
    "un humain",
    "agent humain",
    "operateur humain",
    "passer moi quelqu'un",
    "mettre en relation",
    "je veux un conseiller",
    "je veux parler",
    "personne reelle",
    "bega naa dem ag benn nit",
    "defe ma ak benn conseiller",
    "benn nit",
]

# ── Client signale echec — uniquement si le CLIENT dit que ca n'a pas marche ──
MOTS_ECHEC_CLIENT = [
    "ca ne marche pas",
    "toujours pas resolu",
    "toujours le meme probleme",
    "pas regle",
    "pas resolu",
    "n'a pas resolu",
    "tu n'as pas resolu",
    "toujours bloque",
    "toujours en attente",
    "meme probleme",
    "rien n'a change",
    "ca ne fonctionne toujours pas",
    "pas aide",
    "inutile",
    "duma jappale",  # wolof : ca ne resout rien
]

# ── Litige agent reseau (depot/retrait frauduleux) ────────────────────────────
MOTS_LITIGE_AGENT = [
    "agent a pris mon argent",
    "agent a encaisse sans crediter",
    "depot non credite",
    "agent n'a pas credite",
    "l'agent a pris",
    "agent bi joxoon",
    "dox naa waaye soppaliku du",
    "agent bi defoul",
    "encaisse sans crediter",
]


class MoteurEscalade:

    def evaluer(
        self,
        message: str,
        analyse_nlu: dict,
        contexte,
        transaction: dict = None,
    ) -> dict | None:
        msg_lower = message.lower()
        sentiment = analyse_nlu.get("sentiment", "neutre")
        intention = analyse_nlu.get("intention", {}).get("id", "inconnu")
        entites = analyse_nlu.get("entites", {})
        montant = entites.get("montant_xof")

        # Regle 1 — Fraude / SIM swap
        if self._detecter_fraude(transaction, msg_lower):
            return self._construire("fraude_sim_swap", message)

        # Regle 2 — Montant eleve
        if montant and montant > 500000:
            return self._construire("montant_eleve", message, {"montant": montant})
        if transaction and transaction.get("montant_xof", 0) > 500000:
            return self._construire("montant_eleve", message,
                                    {"montant": transaction["montant_xof"]})

        # Regle 3 — Frustration forte
        if sentiment == "frustre":
            return self._construire("frustration_client", message)

        # Regle 5 — Demande humain EXPLICITE
        # Verifier avec des phrases completes, pas juste le mot "agent"
        if self._detecter_demande_humain_explicite(msg_lower):
            return self._construire("demande_humain", message)

        # Regle 6 — Litige agent reseau
        # Uniquement si intention depot_non_credite OU phrases specifiques litige
        if self._detecter_litige_agent(intention, msg_lower, transaction):
            return self._construire("litige_agent", message)

        # Regle 4 — Echec resolution signale EXPLICITEMENT par le client
        # Ne se declenche PAS automatiquement — uniquement si le client le dit
        if self._detecter_echec_signale_client(msg_lower):
            return self._construire("echec_resolution", message)

        return None

    def _detecter_fraude(self, transaction: dict, msg_lower: str) -> bool:
        if any(mot in msg_lower for mot in MOTS_FRAUDE):
            return True
        if transaction:
            signalements = transaction.get("signalements_fraude", [])
            if any(s in ["sim_swap_suspecte", "fraude_suspectee"] for s in signalements):
                return True
        return False

    def _detecter_demande_humain_explicite(self, msg_lower: str) -> bool:
        """
        Detecte uniquement les demandes explicites de parler a un humain.
        Ne se declenche PAS sur le mot 'agent' seul.
        """
        return any(phrase in msg_lower for phrase in MOTS_DEMANDE_HUMAIN_EXPLICITE)

    def _detecter_litige_agent(
        self, intention: str, msg_lower: str, transaction: dict
    ) -> bool:
        """
        Detecte un litige avec un agent reseau.
        Se base sur l'intention NLU ou des phrases specifiques de litige.
        NE se declenche PAS juste parce que le mot 'agent' est mentionne.
        """
        if intention == "depot_non_credite":
            return True
        if any(phrase in msg_lower for phrase in MOTS_LITIGE_AGENT):
            return True
        if transaction:
            litige = transaction.get("litige", {})
            if litige.get("type") in ["fraude_agent", "encaissement_sans_credit"]:
                return True
        return False

    def _detecter_echec_signale_client(self, msg_lower: str) -> bool:
        """
        Detecte uniquement si le CLIENT signale lui-meme que le probleme
        n'est pas resolu. Pas de compteur automatique.
        """
        return any(phrase in msg_lower for phrase in MOTS_ECHEC_CLIENT)

    def _construire(self, id_regle: str, message: str, donnees: dict = None) -> dict:
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
                f"Je transfere immediatement votre demande a notre equipe specialisee. "
                f"Un conseiller vous contactera dans moins de {delai}. "
                f"Vos fonds sont en securite."
            )
        return (
            f"{nom_client}, je transfere votre demande a un conseiller "
            f"qui pourra mieux vous aider. "
            f"Vous serez contacte(e) dans {delai}. "
            f"Merci de votre patience."
        )
