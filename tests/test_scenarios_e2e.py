"""
Tests E2E des 6 scenarios de demonstration.
Teste le flux complet sans Gemini (mock de la generation LLM).
Lance avec : pytest tests/test_scenarios_e2e.py -v
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_core.dialogue.context_manager import GestionnaireContexte, ContexteConversation
from ai_core.dialogue.escalade_engine import MoteurEscalade


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def gestionnaire():
    """Gestionnaire de contexte sans Redis (mode memoire)."""
    return GestionnaireContexte(redis_client=None)


@pytest.fixture
def moteur():
    return MoteurEscalade()


# ── Tests NLU ─────────────────────────────────────────────────────────────────

class TestAnalyseMessages:
    """Verifie que les messages des scenarios sont correctement analyses."""

    def test_s1_faq_intention(self):
        from ai_core.nlu.intent_classifier import classifier_intention
        res = classifier_intention("quels sont les frais de transfert Wave")
        assert res["id"] == "frais_et_limites"

    def test_s1_solde_wolof(self):
        from ai_core.nlu.intent_classifier import classifier_intention
        res = classifier_intention("sama solde bi")
        assert res["id"] == "consulter_solde"

    def test_s2_transaction_non_recue(self):
        from ai_core.nlu.intent_classifier import classifier_intention
        res = classifier_intention("mon transfert n'est pas arrive")
        assert res["id"] == "transaction_non_recue"

    def test_s3_fraude_detectee(self):
        from ai_core.nlu.sentiment import detecter_sentiment
        assert detecter_sentiment("mon compte a ete pirate arnaque") == "frustre"

    def test_s4_depot_non_credite(self):
        from ai_core.nlu.intent_classifier import classifier_intention
        res = classifier_intention("l'agent a pris mon argent sans crediter mon compte")
        assert res["id"] in ["depot_non_credite", "retrait_echoue"]

    def test_s4_wolof_depot(self):
        from ai_core.nlu.language_detect import detecter_langue
        res = detecter_langue("agent bi joxoon ma xaalis waaye compte bi soppaliku")
        assert res["langue"] in ["wo", "fr-wo"]

    def test_s5_demande_conseiller(self):
        from ai_core.nlu.intent_classifier import classifier_intention
        res = classifier_intention("je veux parler a un conseiller")
        assert res["id"] == "demander_conseiller"


# ── Tests Escalade ─────────────────────────────────────────────────────────────

class TestEscaladeScenarios:
    """Verifie les regles d'escalade pour chaque scenario."""

    def test_s3_escalade_fraude(self, moteur):
        """S3 : message de fraude => escalade P1"""
        from ai_core.dialogue.context_manager import ContexteConversation
        ctx = ContexteConversation("s3", "+221774567890", "chat")
        analyse = {
            "sentiment": "frustre",
            "intention": {"id": "fraude_suspectee"},
            "entites": {"montant_xof": None},
        }
        res = moteur.evaluer("mon compte a ete pirate", analyse, ctx)
        assert res is not None
        assert res["regle"]["priorite"] == "P1"

    def test_s4_escalade_agent(self, moteur):
        """S4 : depot non credite => escalade P2 litige agent"""
        ctx = ContexteConversation("s4", "+221783456789", "chat")
        analyse = {
            "sentiment": "negatif",
            "intention": {"id": "depot_non_credite"},
            "entites": {"montant_xof": None},
        }
        res = moteur.evaluer("agent n'a pas credite", analyse, ctx)
        assert res is not None
        assert res["regle"]["id"] == "litige_agent"
        assert res["regle"]["priorite"] == "P2"

    def test_s2_pas_escalade(self, moteur):
        """S2 : transaction non recue classique => pas d'escalade directe"""
        ctx = ContexteConversation("s2", "+221781234567", "chat")
        analyse = {
            "sentiment": "neutre",
            "intention": {"id": "transaction_non_recue"},
            "entites": {"montant_xof": 25000},
        }
        res = moteur.evaluer("mon transfert n'est pas arrive", analyse, ctx)
        # 25000 < 500000 donc pas d'escalade montant
        assert res is None or res["regle"]["id"] != "montant_eleve"

    def test_s3_montant_eleve_escalade(self, moteur):
        """S3 : montant 600000 > 500000 => escalade P1"""
        ctx = ContexteConversation("s3b", "+221774567890", "chat")
        analyse = {
            "sentiment": "neutre",
            "intention": {"id": "transaction_non_recue"},
            "entites": {"montant_xof": 600000},
        }
        res = moteur.evaluer("j'ai envoye 600000", analyse, ctx)
        assert res is not None
        assert res["regle"]["id"] == "montant_eleve"


# ── Tests Mocks API ────────────────────────────────────────────────────────────

class TestMocksAPIScenarios:

    def test_s1_client_wave_charge(self):
        from backend.mocks.mobile_money_api import obtenir_client_par_telephone
        client = obtenir_client_par_telephone("+221771234567")
        assert client["operateur"] == "wave"
        assert client["langue"] == "fr"

    def test_s1_solde_correct(self):
        from backend.mocks.mobile_money_api import obtenir_solde
        res = obtenir_solde("+221771234567")
        assert res["solde_xof"] == 45200

    def test_s2_transaction_remboursable(self):
        from backend.mocks.mobile_money_api import obtenir_statut_transaction
        res = obtenir_statut_transaction("WV-20260326-8847")
        assert res["succes"] is True
        txn = res["transaction"]
        assert txn["remboursement_eligible"] is True

    def test_s4_agent_frauduleux(self):
        from backend.mocks.agents_network import obtenir_agent, verifier_disponibilite_agent
        res = obtenir_agent("AGT-TBK-0017")
        assert res["succes"] is True
        assert res["agent"]["statut"] == "suspendu"
        dispo = verifier_disponibilite_agent("AGT-TBK-0017")
        assert dispo["disponible"] is False

    def test_s5_ussd_navigation(self):
        from backend.mocks.ussd_api import traiter_requete_ussd
        # Menu principal
        res = traiter_requete_ussd("sess_e2e_001", "+221784567890", "")
        assert res["succes"] is True
        assert "CON" in res["reponse"]
        assert "1." in res["reponse"]

        # Choisir option 2 (Signaler transaction)
        res2 = traiter_requete_ussd("sess_e2e_001", "+221784567890", "2")
        assert "CON" in res2["reponse"]
        assert "2." in res2["reponse"]

        # Choisir 2*2 (Retrait echoue)
        res3 = traiter_requete_ussd("sess_e2e_001", "+221784567890", "2*2")
        assert "END" in res3["reponse"]
        assert res3["statut_session"] == "termine"


# ── Test contexte ─────────────────────────────────────────────────────────────

class TestContexteConversation:

    def test_creation_contexte(self):
        ctx = ContexteConversation("test_001", "+221771234567", "chat")
        assert ctx.id_session == "test_001"
        assert ctx.authentifie is False
        assert ctx.langue == "fr"

    def test_ajout_messages(self):
        ctx = ContexteConversation("test_002", "+221771234567")
        ctx.ajouter_message("human", "Bonjour")
        ctx.ajouter_message("assistant", "Bonjour !")
        assert len(ctx.historique) == 2

    def test_serialisation_roundtrip(self):
        ctx = ContexteConversation("test_003", "+221771234567", "whatsapp")
        ctx.authentifie = True
        ctx.langue = "wo"
        ctx.ajouter_message("human", "test")

        data = ctx.to_dict()
        ctx2 = ContexteConversation.from_dict(data)

        assert ctx2.id_session == ctx.id_session
        assert ctx2.authentifie is True
        assert ctx2.langue == "wo"
        assert len(ctx2.historique) == 1

    def test_historique_max(self):
        from ai_core.dialogue.context_manager import MAX_HISTORIQUE
        ctx = ContexteConversation("test_004", "+221771234567")
        for i in range(MAX_HISTORIQUE + 5):
            ctx.ajouter_message("human", f"message {i}")
        assert len(ctx.historique) == MAX_HISTORIQUE

    @pytest.mark.asyncio
    async def test_gestionnaire_memoire(self, gestionnaire):
        ctx = await gestionnaire.creer("sess_gm_001", "+221771234567", "chat")
        assert ctx is not None

        ctx.ajouter_message("human", "test")
        await gestionnaire.sauvegarder(ctx)

        ctx2 = await gestionnaire.obtenir("sess_gm_001")
        assert ctx2 is not None
        assert len(ctx2.historique) == 1