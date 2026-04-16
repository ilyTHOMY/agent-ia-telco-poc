"""
Mock Email API — simule l'envoi d'emails via SendGrid.
En production : remplacer par sendgrid.SendGridAPIClient.
"""
from datetime import datetime, timezone

_emails_envoyes: list = []


def _horodatage() -> str:
    return datetime.now(timezone.utc).isoformat()


def envoyer_email(
    destinataire: str,
    sujet: str,
    corps_texte: str,
    corps_html: str = None,
    id_ticket: str = None,
) -> dict:
    """Envoie un email au client (simule en PoC)."""
    email = {
        "id": f"EMAIL-{len(_emails_envoyes)+1:04d}",
        "destinataire": destinataire,
        "sujet": sujet,
        "corps_texte": corps_texte,
        "corps_html": corps_html,
        "id_ticket": id_ticket,
        "statut": "envoye",
        "horodatage": _horodatage(),
    }
    _emails_envoyes.append(email)
    print(f"[EMAIL] -> {destinataire} | {sujet}")
    return {"succes": True, "email": email}


def envoyer_rapport_incident(destinataire: str, id_ticket: str, pdf_bytes: bytes = None) -> dict:
    """Envoie le rapport d'incident par email avec PDF en piece jointe."""
    sujet = f"Rapport d'incident — {id_ticket}"
    corps = (
        f"Bonjour,\n\n"
        f"Veuillez trouver ci-joint le rapport d'incident reference {id_ticket}.\n\n"
        f"Notre equipe traite votre demande dans les meilleurs delais.\n\n"
        f"Cordialement,\nService Support Mobile Money"
    )
    email = {
        "id": f"EMAIL-{len(_emails_envoyes)+1:04d}",
        "destinataire": destinataire,
        "sujet": sujet,
        "corps_texte": corps,
        "id_ticket": id_ticket,
        "piece_jointe": f"rapport-{id_ticket}.pdf" if pdf_bytes else None,
        "statut": "envoye",
        "horodatage": _horodatage(),
    }
    _emails_envoyes.append(email)
    print(f"[EMAIL-RAPPORT] -> {destinataire} | {id_ticket}")
    return {"succes": True, "email": email}


def lister_emails(destinataire: str = None) -> dict:
    """Retourne l'historique des emails envoyes."""
    emails = _emails_envoyes if not destinataire else [e for e in _emails_envoyes if e["destinataire"] == destinataire]
    return {"succes": True, "emails": emails, "total": len(emails)}
