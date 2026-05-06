import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMobileMoneAPI:
    def setup_method(self):
        from backend.mocks.mobile_money_api import (
            obtenir_client_par_telephone, obtenir_solde,
            verifier_statut_compte, obtenir_historique_transactions,
            declencher_remboursement,
        )
        self.obtenir_client = obtenir_client_par_telephone
        self.obtenir_solde = obtenir_solde
        self.verifier_statut = verifier_statut_compte
        self.historique = obtenir_historique_transactions
        self.remboursement = declencher_remboursement

    def test_client_wave_existe(self):
        client = self.obtenir_client("+221771234567")
        assert client is not None
        assert client["operateur"] == "wave"
        assert client["nom"] == "Moussa Diallo"

    def test_client_introuvable(self):
        client = self.obtenir_client("+221700000000")
        assert client is None

    def test_solde_client_connu(self):
        res = self.obtenir_solde("+221771234567")
        assert res["succes"] is True
        assert res["solde_xof"] == 45200

    def test_solde_client_inconnu(self):
        res = self.obtenir_solde("+221700000000")
        assert res["succes"] is False

    def test_statut_compte_actif(self):
        res = self.verifier_statut("+221771234567")
        assert res["succes"] is True
        assert res["statut_compte"] == "actif"

    def test_statut_compte_bloque(self):
        res = self.verifier_statut("+221772345678")
        assert res["succes"] is True
        assert res["statut_compte"] == "bloque"

    def test_historique_transactions(self):
        res = self.historique("+221771234567", limite=5)
        assert res["succes"] is True
        assert isinstance(res["transactions"], list)

    def test_remboursement_eligible(self):
        res = self.remboursement("TXN-WAVE-2026-00142")
        assert res["succes"] is True
        assert "montant_rembourse_xof" in res

    def test_remboursement_non_eligible(self):
        res = self.remboursement("TXN-OM-2026-00789")
        assert res["succes"] is False


class TestCRMApi:
    def test_creer_et_obtenir_ticket(self):
        from backend.mocks.crm_api import creer_ticket, obtenir_ticket
        res = creer_ticket(
            telephone="+221771234567",
            type_reclamation="transaction_non_recue",
            description="Test ticket",
            priorite="P2",
        )
        assert res["succes"] is True
        ticket = res["ticket"]
        assert ticket["statut"] == "ouvert"

        res2 = obtenir_ticket(ticket["id"])
        assert res2["succes"] is True
        assert res2["ticket"]["id"] == ticket["id"]

    def test_priorite_invalide_devient_p3(self):
        from backend.mocks.crm_api import creer_ticket
        res = creer_ticket(
            telephone="+221771234567",
            type_reclamation="test",
            description="Test",
            priorite="P9",
        )
        assert res["ticket"]["priorite"] == "P3"


class TestAgentsNetwork:
    def test_obtenir_agent_existant(self):
        from backend.mocks.agents_network import obtenir_agent
        res = obtenir_agent("AGT-DKR-0042")
        assert res["succes"] is True
        assert res["agent"]["nom"] is not None

    def test_agent_introuvable(self):
        from backend.mocks.agents_network import obtenir_agent
        res = obtenir_agent("AGT-INEXISTANT")
        assert res["succes"] is False

    def test_agents_proches_dakar(self):
        from backend.mocks.agents_network import lister_agents_proches
        res = lister_agents_proches(14.6937, -17.4441, operateur="wave")
        assert res["succes"] is True
        agents = res["agents"]
        # Tous les agents retournes doivent etre en_ligne
        for a in agents:
            assert a["statut"] == "en_ligne"