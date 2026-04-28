"""
Tests des canaux — WhatsApp webhook, USSD, Email entrant.
Lance avec : pytest tests/test_canaux.py -v
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestUSSD:
    """Tests du canal USSD."""

    def test_menu_principal(self):
        from backend.mocks.ussd_api import traiter_requete_ussd
        res = traiter_requete_ussd("sess_test_001", "+221781234567", "")
        assert res["succes"] is True
        assert "CON" in res["reponse"]
        assert "1." in res["reponse"]

    def test_option_solde(self):
        from backend.mocks.ussd_api import traiter_requete_ussd
        res = traiter_requete_ussd("sess_test_002", "+221781234567", "1")
        assert res["succes"] is True
        assert "END" in res["reponse"]

    def test_option_signaler_transaction(self):
        from backend.mocks.ussd_api import traiter_requete_ussd
        res = traiter_requete_ussd("sess_test_003", "+221781234567", "2")
        assert res["succes"] is True
        assert "CON" in res["reponse"]
        assert "Retrait" in res["reponse"] or "2." in res["reponse"]

    def test_navigation_retrait_echoue(self):
        from backend.mocks.ussd_api import traiter_requete_ussd
        traiter_requete_ussd("sess_test_004", "+221781234567", "")
        res = traiter_requete_ussd("sess_test_004", "+221781234567", "2*2")
        assert res["succes"] is True
        assert "END" in res["reponse"]
        assert res["statut_session"] == "termine"

    def test_option_invalide(self):
        from backend.mocks.ussd_api import traiter_requete_ussd
        res = traiter_requete_ussd("sess_test_005", "+221781234567", "9")
        assert res["succes"] is True
        assert "END" in res["reponse"]
        assert "invalide" in res["reponse"].lower()

    def test_session_stockee(self):
        from backend.mocks.ussd_api import traiter_requete_ussd, obtenir_session_ussd
        traiter_requete_ussd("sess_test_006", "+221781234567", "")
        res = obtenir_session_ussd("sess_test_006")
        assert res["succes"] is True
        assert res["session"]["telephone"] == "+221781234567"

    def test_lister_sessions(self):
        from backend.mocks.ussd_api import lister_sessions_ussd
        res = lister_sessions_ussd()
        assert res["succes"] is True
        assert isinstance(res["sessions"], list)


class TestWhatsApp:
    """Tests du canal WhatsApp."""

    def test_recevoir_message(self):
        from backend.mocks.whatsapp_api import recevoir_message
        res = recevoir_message("+221771234567", "Bonjour", "Moussa")
        assert res["succes"] is True
        assert res["message"]["telephone"] == "+221771234567"
        assert res["message"]["message"] == "Bonjour"

    def test_envoyer_message(self):
        from backend.mocks.whatsapp_api import envoyer_message
        res = envoyer_message("+221771234567", "Bonjour Moussa !")
        assert res["succes"] is True
        assert res["message"]["statut"] == "envoye"

    def test_verification_webhook_ok(self):
        from backend.mocks.whatsapp_api import verifier_webhook
        challenge = verifier_webhook("subscribe", "test_challenge", "test_challenge")
        assert challenge == "test_challenge"

    def test_verification_webhook_ko(self):
        from backend.mocks.whatsapp_api import verifier_webhook
        challenge = verifier_webhook("subscribe", "bad_token", "correct_token")
        assert challenge is None

    def test_lister_messages(self):
        from backend.mocks.whatsapp_api import recevoir_message, lister_messages
        recevoir_message("+221781234567", "Test message", "Aminata")
        res = lister_messages(telephone="+221781234567")
        assert res["succes"] is True
        assert res["total_entrants"] >= 1


class TestEmail:
    """Tests du canal Email."""

    def test_envoyer_email_simple(self):
        from backend.mocks.email_api import envoyer_email
        res = envoyer_email(
            destinataire="client@test.com",
            sujet="Test support",
            corps_texte="Corps du message",
        )
        assert res["succes"] is True
        assert res["email"]["statut"] == "envoye"

    def test_envoyer_rapport_incident(self):
        from backend.mocks.email_api import envoyer_rapport_incident
        res = envoyer_rapport_incident("client@test.com", "INC-TEST-00001")
        assert res["succes"] is True
        assert "INC-TEST-00001" in res["email"]["sujet"]

    def test_lister_emails(self):
        from backend.mocks.email_api import envoyer_email, lister_emails
        envoyer_email("dest@test.com", "Sujet", "Corps")
        res = lister_emails(destinataire="dest@test.com")
        assert res["succes"] is True
        assert res["total"] >= 1


class TestNotifications:
    """Tests du service de notifications."""

    def test_envoyer_sms(self):
        from backend.mocks.notifications import envoyer_sms
        res = envoyer_sms("+221771234567", "Votre ticket INC-001 est ouvert.")
        assert res["succes"] is True
        assert res["notification"]["canal"] == "sms"

    def test_envoyer_whatsapp_notif(self):
        from backend.mocks.notifications import envoyer_whatsapp
        res = envoyer_whatsapp("+221771234567", "Bonjour via WhatsApp")
        assert res["succes"] is True

    def test_notifier_resolution(self):
        from backend.mocks.notifications import notifier_resolution
        res = notifier_resolution("+221771234567", "INC-TEST-001", canal="sms")
        assert res["succes"] is True
        assert "INC-TEST-001" in res["notification"]["message"]

    def test_notifier_escalade(self):
        from backend.mocks.notifications import notifier_escalade
        res = notifier_escalade("+221771234567", "INC-TEST-002", "5 minutes", canal="sms")
        assert res["succes"] is True

    def test_lister_notifications(self):
        from backend.mocks.notifications import envoyer_sms, lister_notifications
        envoyer_sms("+221771234567", "Test listing")
        res = lister_notifications(telephone="+221771234567")
        assert res["succes"] is True
        assert res["total"] >= 1
