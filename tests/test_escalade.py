import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_core.dialogue.escalade_engine import MoteurEscalade


class MockContexte:
    def __init__(self, incomprehensions=0, tentatives=0):
        self.incomprehensions_consecutives = incomprehensions
        self.tentatives_resolution = tentatives
        self.transaction_courante = None


class TestEscaladeV2:

    def setup_method(self):
        self.moteur = MoteurEscalade()
        self.analyse_neutre = {
            "sentiment": "neutre",
            "intention": {"id": "inconnu"},
            "entites": {"montant_xof": None},
        }

    # ── Regle 1 : Fraude ──────────────────────────────────────────────────────

    def test_fraude_mot_arnaque(self):
        ctx = MockContexte()
        res = self.moteur.evaluer("c'est une arnaque", self.analyse_neutre, ctx)
        assert res is not None
        assert res["regle"]["id"] == "fraude_sim_swap"
        assert res["regle"]["priorite"] == "P1"

    def test_fraude_sim_swap(self):
        ctx = MockContexte()
        res = self.moteur.evaluer("je pense que j'ai eu un sim swap", self.analyse_neutre, ctx)
        assert res is not None
        assert res["regle"]["id"] == "fraude_sim_swap"

    def test_fraude_compte_vide(self):
        ctx = MockContexte()
        res = self.moteur.evaluer("quelqu'un utilise mon compte", self.analyse_neutre, ctx)
        assert res is not None
        assert res["regle"]["id"] == "fraude_sim_swap"

    # ── Regle 2 : Montant eleve ───────────────────────────────────────────────

    def test_montant_eleve_avec_intention_financiere(self):
        ctx = MockContexte()
        analyse = {
            "sentiment": "neutre",
            "intention": {"id": "transaction_non_recue"},
            "entites": {"montant_xof": 600000},
        }
        res = self.moteur.evaluer("j'ai envoye 600000 XOF", analyse, ctx)
        assert res is not None
        assert res["regle"]["id"] == "montant_eleve"

    def test_montant_eleve_SANS_intention_financiere(self):
        """Montant eleve sans contexte financier = pas d'escalade"""
        ctx = MockContexte()
        analyse = {
            "sentiment": "neutre",
            "intention": {"id": "frais_et_limites"},  # pas financiere
            "entites": {"montant_xof": 600000},
        }
        res = self.moteur.evaluer("les frais pour 600000 XOF ?", analyse, ctx)
        # Pas d'escalade — c'est juste une question sur les frais
        assert res is None

    def test_montant_sous_seuil(self):
        ctx = MockContexte()
        analyse = {
            "sentiment": "neutre",
            "intention": {"id": "transaction_non_recue"},
            "entites": {"montant_xof": 25000},
        }
        res = self.moteur.evaluer("transfert 25000 XOF", analyse, ctx)
        assert res is None

    # ── Regle 6 : Litige agent vs Demande humain ──────────────────────────────

    def test_litige_agent_depot_non_credite_intention(self):
        """Intention depot_non_credite = litige agent, PAS demande humain"""
        ctx = MockContexte()
        analyse = {
            "sentiment": "neutre",
            "intention": {"id": "depot_non_credite"},
            "entites": {"montant_xof": None},
        }
        res = self.moteur.evaluer("probleme avec un agent", analyse, ctx)
        assert res is not None
        assert res["regle"]["id"] == "litige_agent"
        assert res["regle"]["id"] != "demande_humain"

    def test_litige_agent_mots_cles(self):
        ctx = MockContexte()
        res = self.moteur.evaluer(
            "l'agent a pris mon argent sans crediter", self.analyse_neutre, ctx)
        assert res is not None
        assert res["regle"]["id"] == "litige_agent"

    def test_litige_agent_boutique(self):
        ctx = MockContexte()
        res = self.moteur.evaluer(
            "la boutique a encaisse sans crediter", self.analyse_neutre, ctx)
        assert res is not None
        assert res["regle"]["id"] == "litige_agent"

    def test_demande_humain_explicite(self):
        """Seulement si le client dit EXPLICITEMENT vouloir un humain"""
        ctx = MockContexte()
        res = self.moteur.evaluer(
            "je veux parler a un conseiller humain", self.analyse_neutre, ctx)
        assert res is not None
        assert res["regle"]["id"] == "demande_humain"

    def test_pas_demande_humain_si_juste_agent(self):
        """'agent' seul ne doit PAS declencher demande_humain"""
        ctx = MockContexte()
        res = self.moteur.evaluer("probleme avec un agent", self.analyse_neutre, ctx)
        # Doit etre litige_agent ou None, jamais demande_humain
        if res:
            assert res["regle"]["id"] != "demande_humain"

    # ── Regle 4 : Echec resolution ────────────────────────────────────────────

    def test_echec_resolution_apres_2_incomprehensions(self):
        """Escalade seulement apres 2 incomprehensions consecutives"""
        ctx = MockContexte(incomprehensions=2)
        res = self.moteur.evaluer("toujours pas resolu", self.analyse_neutre, ctx)
        assert res is not None
        assert res["regle"]["id"] == "echec_resolution"

    def test_pas_escalade_apres_1_incomprehension(self):
        """1 seule incomprehension = pas d'escalade"""
        ctx = MockContexte(incomprehensions=1)
        res = self.moteur.evaluer("je comprends pas", self.analyse_neutre, ctx)
        assert res is None

    def test_pas_escalade_messages_normaux(self):
        """Messages normaux ne declenchent pas l'escalade"""
        ctx = MockContexte(incomprehensions=0)
        analyse = {
            "sentiment": "neutre",
            "intention": {"id": "consulter_solde"},
            "entites": {"montant_xof": None},
        }
        res = self.moteur.evaluer("quel est mon solde", analyse, ctx)
        assert res is None

    # ── Regle 3 : Frustration ─────────────────────────────────────────────────

    def test_frustration(self):
        ctx = MockContexte()
        analyse = {**self.analyse_neutre, "sentiment": "frustre"}
        res = self.moteur.evaluer("c'est inadmissible", analyse, ctx)
        assert res is not None
        assert res["regle"]["id"] == "frustration_client"

    # ── Messages escalade ─────────────────────────────────────────────────────

    def test_message_escalade_fr_p1(self):
        ctx = MockContexte()
        analyse = {**self.analyse_neutre}
        escalade = {
            "regle": next(r for r in __import__(
                'ai_core.dialogue.escalade_engine',
                fromlist=['REGLES_ESCALADE']).REGLES_ESCALADE
                if r["id"] == "fraude_sim_swap"),
            "message_declencheur": "arnaque",
            "donnees": {},
        }
        msg = self.moteur.generer_message_escalade(escalade, langue="fr", nom_client="Moussa")
        assert "Moussa" in msg
        assert len(msg) > 30

    def test_message_escalade_wolof(self):
        from ai_core.dialogue.escalade_engine import REGLES_ESCALADE
        escalade = {
            "regle": next(r for r in REGLES_ESCALADE if r["id"] == "litige_agent"),
            "message_declencheur": "agent bi",
            "donnees": {},
        }
        msg = self.moteur.generer_message_escalade(escalade, langue="wo", nom_client="Fatou")
        assert "Fatou" in msg