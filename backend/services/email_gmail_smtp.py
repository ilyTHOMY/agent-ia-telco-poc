"""
Notification email via Gmail SMTP — aucun service tiers requis.
Utilise ton compte Gmail directement.

Setup (2 minutes) :
1. Va sur myaccount.google.com > Securite > Validation en deux etapes (activer)
2. Cherche "Mots de passe des applications" dans la recherche Google Account
3. Cree un mot de passe pour "Mail" / "Autre" → copie les 16 caracteres
4. Dans .env :
   GMAIL_USER=ton.email@gmail.com
   GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx  (les 16 caracteres)
   EMAIL_DESTINATAIRE=ton.email@gmail.com
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone


def envoyer_email_ticket(ticket: dict) -> dict:
    """
    Envoie un email Gmail quand un ticket est cree.
    Si non configure, skipped silencieusement.
    """
    gmail_user  = os.getenv("GMAIL_USER", "")
    gmail_pass  = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "")
    destinataire = os.getenv("EMAIL_DESTINATAIRE", "")

    if not gmail_user or not gmail_pass or not destinataire:
        print("[EMAIL] Gmail non configure — skipped.")
        print("[EMAIL] Ajoute GMAIL_USER, GMAIL_APP_PASSWORD, EMAIL_DESTINATAIRE dans .env")
        return {"succes": False, "raison": "non_configure"}

    priorite  = ticket.get("priorite", "P3")
    type_rec  = ticket.get("type_reclamation", "inconnu").replace("_", " ")
    telephone = ticket.get("telephone", "—")
    id_ticket = ticket.get("id", "—")
    canal     = ticket.get("canal_origine", "—")
    desc      = ticket.get("description", "—")[:300]
    sla       = ticket.get("sla_heures", 24)
    date      = ticket.get("date_ouverture", "")[:19].replace("T", " ")

    emoji = "🚨" if priorite == "P1" else "⚠️" if priorite == "P2" else "📋"
    sujet = f"{emoji} [{priorite}] Ticket {id_ticket} — {type_rec}"

    corps_html = f"""
<div style="font-family:Arial,sans-serif;max-width:580px;margin:0 auto">
  <div style="background:{'#dc2626' if priorite=='P1' else '#d97706' if priorite=='P2' else '#2563eb'};
              color:white;padding:16px 20px;border-radius:8px 8px 0 0">
    <h2 style="margin:0;font-size:18px">{emoji} Nouveau ticket — Priorite {priorite}</h2>
    <p style="margin:4px 0 0;opacity:.85;font-size:13px">Agent IA Support Mobile Money UEMOA</p>
  </div>
  <div style="background:white;padding:20px;border:1px solid #e5e7eb;border-radius:0 0 8px 8px">
    <table style="width:100%;border-collapse:collapse;font-size:14px">
      <tr style="border-bottom:1px solid #f3f4f6">
        <td style="padding:8px;color:#6b7280;font-weight:600;width:35%">Reference</td>
        <td style="padding:8px;font-family:monospace;color:#2563eb;font-weight:700">{id_ticket}</td>
      </tr>
      <tr style="border-bottom:1px solid #f3f4f6">
        <td style="padding:8px;color:#6b7280;font-weight:600">Type</td>
        <td style="padding:8px;text-transform:capitalize">{type_rec}</td>
      </tr>
      <tr style="border-bottom:1px solid #f3f4f6">
        <td style="padding:8px;color:#6b7280;font-weight:600">Telephone</td>
        <td style="padding:8px;font-family:monospace">{telephone}</td>
      </tr>
      <tr style="border-bottom:1px solid #f3f4f6">
        <td style="padding:8px;color:#6b7280;font-weight:600">Canal</td>
        <td style="padding:8px">{canal}</td>
      </tr>
      <tr style="border-bottom:1px solid #f3f4f6">
        <td style="padding:8px;color:#6b7280;font-weight:600">SLA</td>
        <td style="padding:8px;color:{'#dc2626' if sla<=1 else '#d97706' if sla<=4 else '#059669'};font-weight:600">{sla}h</td>
      </tr>
      <tr style="border-bottom:1px solid #f3f4f6">
        <td style="padding:8px;color:#6b7280;font-weight:600">Date</td>
        <td style="padding:8px">{date}</td>
      </tr>
      <tr>
        <td style="padding:8px;color:#6b7280;font-weight:600;vertical-align:top">Description</td>
        <td style="padding:8px;color:#374151;line-height:1.5">{desc}</td>
      </tr>
    </table>
    <div style="margin-top:16px;padding:10px;background:#f9fafb;border-radius:6px;font-size:12px;color:#6b7280">
      Dashboard : <a href="http://localhost:3000/pages/dashboard.html" style="color:#2563eb">Voir</a>
      &nbsp;·&nbsp;
      PDF : <a href="http://localhost:8000/api/v1/rapports/{id_ticket}/pdf" style="color:#2563eb">Telecharger</a>
    </div>
  </div>
  <p style="text-align:center;color:#9ca3af;font-size:11px;margin-top:10px">
    Agent IA Support Mobile Money · Dakar, Senegal
  </p>
</div>"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = sujet
        msg["From"]    = gmail_user
        msg["To"]      = destinataire
        msg.attach(MIMEText(corps_html, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, destinataire, msg.as_string())

        print(f"[EMAIL] ✓ Email envoye pour {id_ticket} → {destinataire}")
        return {"succes": True, "id_ticket": id_ticket}

    except smtplib.SMTPAuthenticationError:
        print("[EMAIL] ✗ Erreur auth Gmail — verifie GMAIL_USER et GMAIL_APP_PASSWORD")
        return {"succes": False, "raison": "auth_error"}
    except Exception as e:
        print(f"[EMAIL] ✗ Erreur : {e}")
        return {"succes": False, "raison": str(e)}
