from datetime import datetime, timezone

_notifications: list = []


def _horodatage() -> str:
    return datetime.now(timezone.utc).isoformat()


def _enregistrer(notif: dict) -> None:
    _notifications.append(notif)
    print(f"[NOTIF] {notif['canal'].upper()} -> {notif['telephone']} : {notif['message'][:80]}")


def envoyer_sms(telephone: str, message: str, id_ticket: str = None) -> dict:
    """Envoie un SMS au client (simule en PoC)."""
    notif = {
        "id": f"SMS-{len(_notifications)+1:04d}",
        "canal": "sms",
        "telephone": telephone,
        "message": message,
        "id_ticket": id_ticket,
        "statut": "envoye",
        "horodatage": _horodatage(),
    }
    _enregistrer(notif)
    return {"succes": True, "notification": notif}


def envoyer_push(telephone: str, titre: str, message: str, id_ticket: str = None) -> dict:
    """Envoie une notification push (simule en PoC)."""
    notif = {
        "id": f"PUSH-{len(_notifications)+1:04d}",
        "canal": "push",
        "telephone": telephone,
        "titre": titre,
        "message": message,
        "id_ticket": id_ticket,
        "statut": "envoye",
        "horodatage": _horodatage(),
    }
    _enregistrer(notif)
    return {"succes": True, "notification": notif}


def envoyer_whatsapp(telephone: str, message: str, id_ticket: str = None) -> dict:
    """Envoie un message WhatsApp (simule en PoC, vrai en prod via Meta API)."""
    notif = {
        "id": f"WA-{len(_notifications)+1:04d}",
        "canal": "whatsapp",
        "telephone": telephone,
        "message": message,
        "id_ticket": id_ticket,
        "statut": "envoye",
        "horodatage": _horodatage(),
    }
    _enregistrer(notif)
    return {"succes": True, "notification": notif}


def envoyer_email(destinataire: str, sujet: str, corps: str, id_ticket: str = None) -> dict:
    """Envoie un email (simule en PoC, vrai en prod via SendGrid)."""
    notif = {
        "id": f"EMAIL-{len(_notifications)+1:04d}",
        "canal": "email",
        "telephone": destinataire,
        "sujet": sujet,
        "message": corps,
        "id_ticket": id_ticket,
        "statut": "envoye",
        "horodatage": _horodatage(),
    }
    _enregistrer(notif)
    return {"succes": True, "notification": notif}


def notifier_resolution(telephone: str, id_ticket: str, canal: str = "sms") -> dict:
    """Notifie le client que sa reclamation est resolue."""
    message = (
        f"Votre reclamation {id_ticket} a ete resolue avec succes. "
        "Merci de votre confiance. Pour toute question, recontactez-nous."
    )
    if canal == "whatsapp":
        return envoyer_whatsapp(telephone, message, id_ticket)
    elif canal == "push":
        return envoyer_push(telephone, "Reclamation resolue", message, id_ticket)
    elif canal == "email":
        return envoyer_email(telephone, f"Resolution de votre reclamation {id_ticket}", message, id_ticket)
    return envoyer_sms(telephone, message, id_ticket)


def notifier_escalade(telephone: str, id_ticket: str, delai_estime: str, canal: str = "sms") -> dict:
    """Notifie le client que sa demande est escaladee vers un conseiller."""
    message = (
        f"Votre demande {id_ticket} necessite l'intervention d'un conseiller. "
        f"Vous serez contacte dans {delai_estime}. Merci de votre patience."
    )
    if canal == "whatsapp":
        return envoyer_whatsapp(telephone, message, id_ticket)
    return envoyer_sms(telephone, message, id_ticket)


def lister_notifications(telephone: str = None) -> dict:
    """Liste toutes les notifications envoyees."""
    notifs = _notifications if not telephone else [n for n in _notifications if n["telephone"] == telephone]
    return {"succes": True, "notifications": notifs, "total": len(notifs)}
