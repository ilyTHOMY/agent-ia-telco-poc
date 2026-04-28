"""
Classificateur d'intentions v2 — utilise le fichier intents.json unifie
(fusion intents_fr.json + intents_wo.json en un seul fichier).
Point d'entree : analyser_message()
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
    """Score de correspondance entre message et intention par matching mots-cles."""
    msg = message.lower()
    mots_msg = set(msg.split())
    score = 0.0

    for exemple in intent.get("exemples", []):
        mots_ex = set(exemple.lower().split())
        communs = mots_msg & mots_ex
        if communs:
            ratio = len(communs) / max(len(mots_ex), 1)
            score = max(score, ratio)

    return score


def classifier_intention(message: str) -> dict:
    """
    Classifie l'intention principale du message.
    Retourne l'intention avec le meilleur score ou 'inconnu' si < seuil.
    """
    intents = _charger_intents()
    meilleur_score = 0.0
    meilleure = None

    for intent in intents:
        score = _score_intent(message, intent)
        if score > meilleur_score:
            meilleur_score = score
            meilleure = intent

    if meilleur_score < 0.18 or meilleure is None:
        return {
            "id": "inconnu",
            "categorie": "general",
            "confiance": 0.0,
            "resolution": "autonome",
            "priorite": "P4",
            "entites_attendues": [],
        }

    return {
        "id": meilleure["id"],
        "categorie": meilleure["categorie"],
        "confiance": round(meilleur_score, 2),
        "resolution": meilleure["resolution"],
        "priorite": meilleure["priorite"],
        "entites_attendues": meilleure.get("entites", []),
    }


def analyser_message(message: str) -> dict:
    """
    Analyse complete d'un message client.
    Point d'entree unique du module NLU.
    Retourne : intention + entites + sentiment + langue
    """
    return {
        "message": message,
        "intention": classifier_intention(message),
        "entites": extraire_entites(message),
        "sentiment": detecter_sentiment(message),
        "langue": detecter_langue(message),
    }
