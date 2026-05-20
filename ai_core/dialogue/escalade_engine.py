from datetime import datetime, timezone
import re

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
        "seuil_xof": 100000,
    },
    {
        "id": "litige_agent",
        "nom": "Litige avec agent reseau",
        "priorite": "P2",
        "sla_minutes": 120,
        "cible": "responsable_reseau_agents",
    },
    {
        "id": "frustration_client",
        "nom": "Client tres frustre",
        "priorite": "P2",
        "sla_minutes": 10,
        "cible": "conseiller_relation_client",
    },
    {
        "id": "demande_humain",
        "nom": "Client demande explicitement un conseiller humain",
        "priorite": "P2",
        "sla_minutes": 5,
        "cible": "conseiller_disponible",
    },
    {
        "id": "echec_resolution",
        "nom": "Echec de resolution apres 2 incomprehensions consecutives",
        "priorite": "P2",
        "sla_minutes": 30,
        "cible": "conseiller_n2",
    },
]

# ── Mots cles fraude ──────────────────────────────────────────────────────────
MOTS_FRAUDE = [
    "arnaque", "fraude", "vole mon argent", "pirate", "sim swap",
    "vide mon compte", "acces non autorise", "escroquerie",
    "quelqu'un utilise mon compte", "transactions inconnues",
    "transaction que je n'ai pas faite", "je n'ai pas fait cette transaction",
    "dama ko jafe jafe", "ku nekk am sama compte",
]

# ── Mots cles litige agent reseau ─────────────────────────────────────────────
# Tres specifiques pour eviter confusion avec "agent humain"
MOTS_LITIGE_AGENT = [
    "agent a pris mon argent",
    "agent n'a pas credite",
    "agent a encaisse",
    "sans crediter mon compte",
    "depot non credite",
    "agent a refuse",
    "agent frauduleux",
    "boutique n'a pas credite",
    "point wave n'a pas credite",
    "point orange n'a pas credite",
]

# ── Mots cles demande humain explicite ───────────────────────────────────────
# Tres specifiques — "agent" seul est exclu car confus avec "litige agent"
MOTS_DEMANDE_HUMAIN = [
    "parler a un conseiller",
    "parler a quelqu'un",
    "je veux un humain",
    "mettre moi en relation",
    "un agent humain",
    "une vraie personne",
    "passer moi quelqu'un",
    "conseiller humain",
    "operateur humain",
    "je veux parler",
    "transferez moi",
    "bega naa dem ag benn nit",
    "defe ma ak benn conseiller",
]

# ── Mots frustration ──────────────────────────────────────────────────────────
MOTS_FRUSTRATION = [
    "inadmissible", "scandaleux", "inacceptable", "c'est honteux",
    "tres en colere", "en colere", "furieux", "exaspere",
    "ca fait des jours", "ca fait des semaines", "toujours pas resolu",
    "j'en ai marre", "ras le bol", "plus possible",
    "remboursez moi immediatement", "je vais porter plainte",
    "service nul", "catastrophique",
]

# ── Contextes qui NE doivent PAS declencher montant_eleve ────────────────────
# Ex : "j'ai 500 000 XOF sur mon compte" ne doit pas escalader
CONTEXTES_EXCLUS_MONTANT = [
    "mon solde", "mon compte contient", "j'ai sur mon compte",
    "plafond", "limite", "j'ai economise", "j'ai mis de cote",
    "retirer", "deposer", "payer ma facture",
]

# ── Patterns montant dans le texte ───────────────────────────────────────────
PATTERN_MONTANT = re.compile(
    r'(\d[\d\s]{0,6}(?:\d{3}|\d{2}|\d{1}))\s*(?:xof|fcfa|cfa|francs?|f\b)',
    re.IGNORECASE
)
PATTERN_MONTANT_MILLERS = re.compile(r'\b(\d+)\s*000\b')


def _extraire_montant(msg: str) -> int | None:
    """Extrait le montant en XOF depuis le texte brut."""
    # Cherche un montant avec unite monetaire
    m = PATTERN_MONTANT.search(msg)
    if m:
        try:
            val = int(m.group(1).replace(' ', '').replace('\xa0', ''))
            if val >= 1000:
                return val
        except:
            pass
    # Cherche un nombre suivi de "000" (ex: "200 000" ou "200000")
    m2 = PATTERN_MONTANT_MILLERS.search(msg)
    if m2:
        try:
            val = int(m2.group(1)) * 1000
            if val >= 1000:
                return val
        except:
            pass
    return None


class MoteurEscalade:

    def evaluer(
        self,
        message: str,
        analyse_nlu: dict,
        contexte,
        transaction: dict = None,
    ) -> dict | None:
        msg            = message.lower()
        sentiment      = analyse_nlu.get("sentiment", "neutre")
        intention_id   = analyse_nlu.get("intention", {}).get("id", "inconnu")
        montant_nlu    = analyse_nlu.get("entites", {}).get("montant_xof")
        historique     = getattr(contexte, 'historique', [])

        # ── Regle 1 : Fraude / SIM swap ──────────────────────────────────────
        if self._detecter_fraude(msg, transaction, intention_id):
            return self._resultat("fraude_sim_swap", message)

        # ── Regle 2 : Montant eleve ───────────────────────────────────────────
        # Ne pas escalader si le contexte parle de solde/plafond/depot
        contexte_exclu = any(c in msg for c in CONTEXTES_EXCLUS_MONTANT)

        if not contexte_exclu:
            # Montant extrait par NLU
            if montant_nlu and montant_nlu > 100000:
                return self._resultat("montant_eleve", message, {"montant": montant_nlu})

            # Montant extrait du texte brut (si NLU a rate)
            montant_brut = _extraire_montant(msg)
            if montant_brut and montant_brut > 100000:
                # Verifier que le contexte est bien une reclamation (mot cle probleme)
                mots_reclamation = [
                    "refuse", "bloque", "echoue", "pas arrive", "en attente",
                    "n'a pas", "probleme", "pas recu", "urgent", "erreur"
                ]
                if any(m in msg for m in mots_reclamation):
                    return self._resultat("montant_eleve", message, {"montant": montant_brut})

        # ── Regle 3 : Litige agent ────────────────────────────────────────────
        if self._detecter_litige_agent(intention_id, msg, transaction):
            return self._resultat("litige_agent", message)

        # ── Regle 4 : Frustration ─────────────────────────────────────────────
        if sentiment in ("frustre", "tres_frustre") or any(m in msg for m in MOTS_FRUSTRATION):
            return self._resultat("frustration_client", message)

        # ── Regle 5 : Demande humain explicite ───────────────────────────────
        if self._detecter_demande_humain_explicite(msg):
            return self._resultat("demande_humain", message)

        # ── Regle 6 : Echec resolution ────────────────────────────────────────
        nb_incomprehensions = getattr(contexte, 'incomprehensions_consecutives', 0)
        if nb_incomprehensions >= 2:
            return self._resultat("echec_resolution", message)

        return None

    def _detecter_fraude(self, msg: str, transaction: dict, intention_id: str) -> bool:
        # Mots cles fraude dans le message
        if any(mot in msg for mot in MOTS_FRAUDE):
            return True
        # Intention NLU fraude
        if intention_id == "fraude_suspectee":
            return True
        # Signalements dans la transaction
        if transaction:
            signalements = transaction.get("signalements_fraude", [])
            if any(s in ["sim_swap_suspecte", "fraude_suspectee"] for s in signalements):
                return True
        return False

    def _detecter_litige_agent(
        self, intention: str, msg: str, transaction: dict
    ) -> bool:
        # Intention directe depot non credite
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
        return any(mot in msg for mot in MOTS_DEMANDE_HUMAIN)

    def _resultat(self, id_regle: str, message: str, donnees: dict = None) -> dict:
        regle = next(r for r in REGLES_ESCALADE if r["id"] == id_regle)
        return {
            "escalade":           True,
            "regle":              regle,
            "message_declencheur": message,
            "donnees":            donnees or {},
            "horodatage":         datetime.now(timezone.utc).isoformat(),
        }

    def generer_message_escalade(
        self, resultat: dict, langue: str = "fr", nom_client: str = "Client"
    ) -> str:
        regle = resultat["regle"]
        sla   = regle["sla_minutes"]
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