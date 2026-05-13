from datetime import datetime, timezone

_messages_entrants: list = []
_messages_sortants: list = []


def _horodatage() -> str:
    return datetime.now(timezone.utc).isoformat()


def recevoir_message(telephone: str, message: str, nom: str = None) -> dict:
    """Simule la reception d'un message WhatsApp entrant."""
    msg = {
        "id": f"WA-IN-{len(_messages_entrants)+1:04d}",
        "telephone": telephone,
        "nom": nom or "Inconnu",
        "message": message,
        "horodatage": _horodatage(),
        "statut": "recu",
    }
    _messages_entrants.append(msg)
    print(f"[WA-IN] {telephone} : {message}")
    return {"succes": True, "message": msg}


def envoyer_message(telephone: str, message: str, type_message: str = "text") -> dict:
    """Envoie un message WhatsApp sortant (simule en PoC)."""
    msg = {
        "id": f"WA-OUT-{len(_messages_sortants)+1:04d}",
        "telephone": telephone,
        "message": message,
        "type_message": type_message,
        "horodatage": _horodatage(),
        "statut": "envoye",
    }
    _messages_sortants.append(msg)
    print(f"[WA-OUT] -> {telephone} : {message[:60]}")
    return {"succes": True, "message": msg}


def verifier_webhook(token: str, challenge: str, verify_token: str) -> str | None:
    """Verifie le token de validation du webhook Meta."""
    if token == verify_token:
        return challenge
    return None


def lister_messages(telephone: str = None) -> dict:
    """Retourne l'historique des messages WhatsApp."""
    entrants = _messages_entrants if not telephone else [m for m in _messages_entrants if m["telephone"] == telephone]
    sortants = _messages_sortants if not telephone else [m for m in _messages_sortants if m["telephone"] == telephone]
    return {
        "succes": True,
        "entrants": entrants,
        "sortants": sortants,
        "total_entrants": len(entrants),
        "total_sortants": len(sortants),
    }
