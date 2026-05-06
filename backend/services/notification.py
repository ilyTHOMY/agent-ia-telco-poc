from backend.mocks.notifications import (
    envoyer_sms, envoyer_whatsapp, envoyer_email, envoyer_push
)


async def notifier_client(
    telephone: str,
    message: str,
    canal_preference: str = "sms",
    id_ticket: str = None,
) -> dict:
    if canal_preference == "whatsapp":
        return envoyer_whatsapp(telephone, message, id_ticket)
    elif canal_preference == "email":
        return envoyer_email(telephone, "Notification Agent IA", message, id_ticket)
    elif canal_preference == "push":
        return envoyer_push(telephone, "Agent IA Support", message, id_ticket)
    return envoyer_sms(telephone, message, id_ticket)


async def notifier_resolution_ticket(
    telephone: str,
    id_ticket: str,
    canal: str = "sms",
) -> dict:
    """Notifie le client de la resolution de son ticket."""
    message = (
        f"Bonne nouvelle ! Votre reclamation {id_ticket} a ete resolue. "
        "Merci de votre confiance. Pour toute question : recontactez-nous."
    )
    return await notifier_client(telephone, message, canal, id_ticket)
