"""
Tests du moteur d'escalade — 6 regles metier.
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_core.dialogue.escalade_engine import MoteurEscalade


class MockContexte:
    def __init__(self, tentatives=0):
        self.tentatives_resolution = tentatives
        self.transaction_courante = None


class TestMoteurEscalade:
    def setup_method(self):
        self.moteur = MoteurEscalade()
        self.analyse_neutre = {
            "sentiment": "neutre",
            "intention": {"id": "inconnu"},
            "entites": {"montant_xof": None},
        }

    def test_escalade_fraude_message(self):
        """Regle 1 : mot 'arnaque' dans le message"""
        ctx = MockContexte()
        res = self.moteur.evaluer("je pense que c'est une arnaque", self.analyse_neutre, ctx)
        assert res is not None
        assert res["regle"]["id"] == "fraude_sim_swap"
        assert res["regle"]["priorite"] == "P1"

    def test_escalade_montant_eleve(self):
        """Regle 2 : montant > 500 000 XOF"""
        ctx = MockContexte()
        analyse = {**self.analyse_neutre, "entites": {"montant_xof": 600000}}
        res = self.moteur.evaluer("j'ai envoye 600000 XOF", analyse, ctx)
        assert res is not None
        assert res["regle"]["id"] == "montant_eleve"
        assert res["regle"]["priorite"] == "P1"

    def test_escalade_frustration(self):
        """Regle 3 : sentiment frustre"""
        ctx = MockContexte()
        analyse = {**self.analyse_neutre, "sentiment": "frustre"}
        res = self.moteur.evaluer("c'est inacceptable", analyse, ctx)
        assert res is not None
        assert res["regle"]["id"] == "frustration_client"

    def test_escalade_echec_resolution(self):
        """Regle 4 : 2 tentatives echouees"""
        ctx = MockContexte(tentatives=2)
        res = self.moteur.evaluer("toujours pas resolu", self.analyse_neutre, ctx)
        assert res is not None
        assert res["regle"]["id"] == "echec_resolution"

    def test_escalade_demande_humain(self):
        """Regle 5 : demande explicite conseiller"""
        ctx = MockContexte()
        res = self.moteur.evaluer("je veux parler a un conseiller", self.analyse_neutre, ctx)
        assert res is not None
        assert res["regle"]["id"] == "demande_humain"

    def test_escalade_litige_agent(self):
        """Regle 6 : depot non credite"""
        ctx = MockContexte()
        analyse = {**self.analyse_neutre, "intention": {"id": "depot_non_credite"}}
        res = self.moteur.evaluer("l'agent n'a pas credite", analyse, ctx)
        assert res is not None
        assert res["regle"]["id"] == "litige_agent"

    def test_pas_escalade_cas_normal(self):
        """Aucune escalade pour une demande simple"""
        ctx = MockContexte()
        analyse = {**self.analyse_neutre, "intention": {"id": "consulter_solde"}}
        res = self.moteur.evaluer("quel est mon solde", analyse, ctx)
        assert res is None

    def test_montant_sous_seuil(self):
        """Pas d'escalade si montant < 500 000"""
        ctx = MockContexte()
        analyse = {**self.analyse_neutre, "entites": {"montant_xof": 25000}}
        res = self.moteur.evaluer("j'ai envoye 25000", analyse, ctx)
        assert res is None

    def test_message_escalade_fr(self):
        """Message d'escalade en francais"""
        ctx = MockContexte()
        analyse = {**self.analyse_neutre, "sentiment": "frustre"}
        res = self.moteur.evaluer("inacceptable", analyse, ctx)
        msg = self.moteur.generer_message_escalade(res, langue="fr", nom_client="Moussa")
        assert "Moussa" in msg
        assert len(msg) > 20

    def test_message_escalade_wolof(self):
        """Message d'escalade en wolof"""
        ctx = MockContexte()
        analyse = {**self.analyse_neutre, "entites": {"montant_xof": 700000}}
        res = self.moteur.evaluer("j'ai envoye 700000", analyse, ctx)
        msg = self.moteur.generer_message_escalade(res, langue="wo", nom_client="Fatou")
        assert "Fatou" in msg