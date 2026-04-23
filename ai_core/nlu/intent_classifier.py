"""
Classification d'intentions — identifie l'intention principale du message client.
Approche hybride : matching par mots-cles + scoring de similarite simple.
En production, ce module peut etre remplace par un modele fine-tune
ou delegue directement a Gemini avec le dataset d'intentions en contexte.
"""
import json
from pathlib import Path
from ai_core.nlu.entity_extractor import extraire_entites
from ai_core.nlu.sentiment import detecter_sentiment
from ai_core.nlu.language_detect import detecter_langue

DATASET_PATH = Path(__file__).parent / "intents_dataset" / "intents.json"


def _charger_intents() -> list:
    with open(DATASET_PATH, encoding="utf-8") as f:
        return json.load(f)["intents"]


def _score_intent(message: str, intent: dict) -> float:
    """Calcule un score de correspondance entre le message et une intention."""
    msg = message.lower()
    score = 0.0
    tous_exemples = intent.get("exemples_fr", []) + intent.get("exemples_wo", [])

    for exemple in tous_exemples:
        mots_exemple = exemple.lower().split()
        mots_message = msg.split()
        communs = sum(1 for mot in mots_exemple if mot in mots_message)
        if communs > 0:
            ratio = communs / max(len(mots_exemple), 1)
            score = max(score, ratio)

    return score


def classifier_intention(message: str) -> dict:
    """
    Classifie l'intention principale du message.
    Retourne l'intention avec le score le plus eleve.
    Si aucune intention n'est identifiee avec confiance, retourne 'inconnu'.
    """
    intents = _charger_intents()
    meilleur_score = 0.0
    meilleure_intention = None

    for intent in intents:
        score = _score_intent(message, intent)
        if score > meilleur_score:
            meilleur_score = score
            meilleure_intention = intent

    if meilleur_score < 0.2 or meilleure_intention is None:
        return {
            "id": "inconnu",
            "categorie": "general",
            "confiance": 0.0,
            "resolution": "autonome",
            "priorite": "P4",
        }

    return {
        "id": meilleure_intention["id"],
        "categorie": meilleure_intention["categorie"],
        "confiance": round(meilleur_score, 2),
        "resolution": meilleure_intention["resolution"],
        "priorite": meilleure_intention["priorite"],
        "entites_attendues": meilleure_intention.get("entites", []),
    }


def analyser_message(message: str) -> dict:
    """
    Analyse complete d'un message client.
    Combine : intention + entites + sentiment + langue.
    C'est le point d'entree principal du module NLU.
    """
    return {
        "message": message,
        "intention": classifier_intention(message),
        "entites": extraire_entites(message),
        "sentiment": detecter_sentiment(message),
        "langue": detecter_langue(message),
    }
