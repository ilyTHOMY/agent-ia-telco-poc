import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_core.nlu.language_detect import detecter_langue, adapter_langue_reponse
from ai_core.nlu.sentiment import detecter_sentiment, adapter_ton_reponse
from ai_core.nlu.entity_extractor import extraire_entites, extraire_montant, extraire_telephone


class TestLangueDetection:

    def test_message_francais(self):
        res = detecter_langue("mon transfert n'est pas arrive")
        assert res["langue"] == "fr"

    def test_message_wolof(self):
        res = detecter_langue("sama xaalis bi des du ko waaye")
        assert res["langue"] in ["wo", "fr-wo"]

    def test_message_franco_wolof(self):
        res = detecter_langue("mon compte bi dafa seede")
        assert res["langue"] in ["fr-wo", "fr"]

    def test_message_vide(self):
        res = detecter_langue("")
        assert res["langue"] == "fr"
        assert res["confiance"] == 1.0

    def test_instruction_langue_fr(self):
        instr = adapter_langue_reponse("fr")
        assert "francais" in instr.lower()

    def test_instruction_langue_wo(self):
        instr = adapter_langue_reponse("wo")
        assert "wolof" in instr.lower()


class TestSentiment:

    def test_sentiment_frustre(self):
        assert detecter_sentiment("c'est inacceptable cette arnaque") == "frustre"

    def test_sentiment_negatif(self):
        assert detecter_sentiment("mon compte est bloque je ne peux pas") == "negatif"

    def test_sentiment_positif(self):
        assert detecter_sentiment("merci c'est parfait") == "positif"

    def test_sentiment_neutre(self):
        assert detecter_sentiment("bonjour") == "neutre"

    def test_positif_avant_negatif(self):
        # "merci" (positif) avant "probleme" (negatif) => positif
        assert detecter_sentiment("merci pour votre aide malgre mon probleme") == "positif"

    def test_ton_frustre(self):
        ton = adapter_ton_reponse("frustre")
        assert "frustration" in ton.lower() or "frustre" in ton.lower() or "empathie" in ton.lower()


class TestEntityExtraction:

    def test_extraire_montant_simple(self):
        assert extraire_montant("j'ai envoye 25000 XOF") == 25000

    def test_extraire_montant_avec_espace(self):
        assert extraire_montant("montant de 500 000 FCFA") == 500000

    def test_extraire_montant_absent(self):
        assert extraire_montant("mon compte est bloque") is None

    def test_extraire_telephone_senegalais(self):
        tel = extraire_telephone("appelle le +221771234567 pour confirmer")
        assert tel == "+221771234567"

    def test_extraire_telephone_sans_indicatif(self):
        tel = extraire_telephone("mon numero est 771234567")
        assert tel is not None
        assert "221" in tel

    def test_extraire_reference(self):
        from ai_core.nlu.entity_extractor import extraire_reference
        ref = extraire_reference("ma reference est WV-20260326-8847")
        assert ref is not None
        assert "WV" in ref

    def test_extraire_operateur_wave(self):
        from ai_core.nlu.entity_extractor import extraire_operateur
        assert extraire_operateur("j'utilise wave pour mes transferts") == "wave"

    def test_extraire_operateur_orange(self):
        from ai_core.nlu.entity_extractor import extraire_operateur
        assert extraire_operateur("orange money ne fonctionne pas") == "orange_money"

    def test_extraire_fournisseur_senelec(self):
        from ai_core.nlu.entity_extractor import extraire_fournisseur
        assert extraire_fournisseur("ma facture SENELEC n'est pas creditee") == "SENELEC"

    def test_extraire_toutes_entites(self):
        msg = "j'ai envoye 50000 XOF vers +221779876543 via wave reference WV-20260326-1234"
        entites = extraire_entites(msg)
        assert entites["montant_xof"] == 50000
        assert entites["telephone"] is not None
        assert entites["operateur"] == "wave"
        assert entites["reference_transaction"] is not None