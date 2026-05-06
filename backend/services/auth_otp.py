import json
from pathlib import Path
from datetime import datetime, timezone

DONNEES_DIR = Path(__file__).parent.parent.parent / "data"
MAX_TENTATIVES = 3


def _charger_clients() -> list:
    with open(DONNEES_DIR / "clients.json", encoding="utf-8") as f:
        return json.load(f)["clients"]


def verifier_pin(telephone: str, pin: str) -> dict:
    """
    Verifie le PIN d'un client
    """
    clients = _charger_clients()
    client = next((c for c in clients if c["telephone"] == telephone), None)

    if not client:
        return {
            "succes": False,
            "bloque": False,
            "tentatives_restantes": 0,
            "erreur": "Numero non enregistre dans le systeme.",
        }

    if client.get("statut_compte") == "bloque":
        return {
            "succes": False,
            "bloque": True,
            "tentatives_restantes": 0,
            "erreur": "Compte bloque. Contactez votre operateur.",
        }

    tentatives = client.get("tentatives_pin_echouees", 0)

    if tentatives >= MAX_TENTATIVES:
        return {
            "succes": False,
            "bloque": True,
            "tentatives_restantes": 0,
            "erreur": "Compte bloque apres 3 tentatives incorrectes.",
        }

    if str(pin) != str(client.get("pin", "")):
        tentatives_restantes = MAX_TENTATIVES - tentatives - 1
        return {
            "succes": False,
            "bloque": tentatives_restantes <= 0,
            "tentatives_restantes": tentatives_restantes,
            "erreur": f"PIN incorrect. {tentatives_restantes} tentative(s) restante(s).",
        }

    return {
        "succes": True,
        "bloque": False,
        "tentatives_restantes": MAX_TENTATIVES,
        "client": client,
    }