"""
Service email v2 — supporte plusieurs destinataires via EMAIL_DESTINATAIRES (liste separee par virgules).
Compatible avec EMAIL_DESTINATAIRE (ancien .env) pour la retrocompatibilite.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone


def envoyer_email_ticket(ticket: dict) -> dict:
    gmail_user = os.getenv("GMAIL_USER", "")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "")

    # Support multi-destinataires
    destinataires_str = os.getenv(
        "EMAIL_DESTINATAIRES",
        os.getenv("EMAIL_DESTINATAIRE", "")
    )
    destinataires = [e.strip() for e in destinataires_str.split(",") if e.strip()]

    if not gmail_user or not gmail_pass or not destinataires:
        print("[EMAIL] Ajoute GMAIL_USER, GMAIL_APP_PASSWORD, EMAIL_DESTINATAIRES dans .env")
        return {"succes": False, "erreur": "Configuration email manquante"}

    id_ticket     = ticket.get("id", "—")
    telephone     = ticket.get("telephone", "—")
    type_rec      = ticket.get("type_reclamation", "—").replace("_", " ").title()
    priorite      = ticket.get("priorite", "P3")
    statut        = ticket.get("statut", "ouvert")
    canal         = ticket.get("canal_origine", "—")
    description   = ticket.get("description", "—")
    sla           = ticket.get("sla_heures", 24)
    date_ouv      = ticket.get("date_ouverture", "")[:19].replace("T", " ")

    couleurs = {"P1": "#FF5A65", "P2": "#FF8C42", "P3": "#4F6EFF"}
    couleur_prio = couleurs.get(priorite, "#4F6EFF")

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#F0F2FF;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F0F2FF;padding:32px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

      <!-- Header -->
      <tr><td style="background:linear-gradient(135deg,#4F6EFF,#00D4B4);padding:28px 32px;">
        <p style="margin:0;font-size:11px;color:rgba(255,255,255,0.7);letter-spacing:2px;text-transform:uppercase;">Agent IA Support · Mobile Money UEMOA</p>
        <h1 style="margin:8px 0 0;color:white;font-size:22px;">Nouveau ticket créé</h1>
      </td></tr>

      <!-- Bandeau priorité -->
      <tr><td style="background:{couleur_prio};padding:12px 32px;">
        <p style="margin:0;color:white;font-size:14px;font-weight:bold;">
          🚨 Priorité {priorite} — Traitement sous {sla}h — {type_rec}
        </p>
      </td></tr>

      <!-- Corps -->
      <tr><td style="padding:32px;">
        <table width="100%" cellpadding="8" cellspacing="0" style="border-collapse:collapse;">
          <tr style="background:#F8F9FF;">
            <td style="font-size:12px;color:#8B92B8;font-weight:bold;width:40%;padding:10px 12px;">Référence</td>
            <td style="font-size:14px;color:#1C2235;font-family:monospace;padding:10px 12px;">{id_ticket}</td>
          </tr>
          <tr>
            <td style="font-size:12px;color:#8B92B8;font-weight:bold;padding:10px 12px;">Téléphone client</td>
            <td style="font-size:14px;color:#1C2235;padding:10px 12px;">{telephone}</td>
          </tr>
          <tr style="background:#F8F9FF;">
            <td style="font-size:12px;color:#8B92B8;font-weight:bold;padding:10px 12px;">Canal</td>
            <td style="font-size:14px;color:#1C2235;padding:10px 12px;">{canal}</td>
          </tr>
          <tr>
            <td style="font-size:12px;color:#8B92B8;font-weight:bold;padding:10px 12px;">Statut</td>
            <td style="font-size:14px;color:#1C2235;padding:10px 12px;">{statut}</td>
          </tr>
          <tr style="background:#F8F9FF;">
            <td style="font-size:12px;color:#8B92B8;font-weight:bold;padding:10px 12px;">Date d'ouverture</td>
            <td style="font-size:14px;color:#1C2235;padding:10px 12px;">{date_ouv}</td>
          </tr>
          <tr>
            <td style="font-size:12px;color:#8B92B8;font-weight:bold;padding:10px 12px;vertical-align:top;">Description</td>
            <td style="font-size:14px;color:#1C2235;padding:10px 12px;line-height:1.6;">{description}</td>
          </tr>
        </table>

        <!-- CTA -->
        <div style="margin-top:24px;text-align:center;">
          <a href="http://localhost:3000/pages/dashboard.html" 
             style="display:inline-block;background:linear-gradient(135deg,#4F6EFF,#6B86FF);color:white;
                    text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:bold;font-size:14px;margin-right:8px;">
            Voir le dashboard
          </a>
          <a href="http://localhost:8000/api/v1/rapports/{id_ticket}/pdf"
             style="display:inline-block;background:#F0F2FF;color:#4F6EFF;border:1px solid #4F6EFF;
                    text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:bold;font-size:14px;">
            Télécharger le rapport PDF
          </a>
        </div>
      </td></tr>

      <!-- Footer -->
      <tr><td style="background:#F8F9FF;padding:16px 32px;text-align:center;border-top:1px solid #E8ECFF;">
        <p style="margin:0;font-size:11px;color:#8B92B8;">
          Agent IA Support Mobile Money UEMOA · Généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}
        </p>
      </td></tr>

    </table>
  </td></tr>
</table>
</body>
</html>
"""

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            for destinataire in destinataires:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"[{priorite}] Ticket {id_ticket} — {type_rec}"
                msg["From"]    = f"Agent IA Support <{gmail_user}>"
                msg["To"]      = destinataire
                msg.attach(MIMEText(html, "html"))
                server.sendmail(gmail_user, destinataire, msg.as_string())
                print(f"[EMAIL] ✓ Email envoye → {destinataire}")

        return {"succes": True, "destinataires": destinataires, "ticket": id_ticket}

    except Exception as e:
        print(f"[EMAIL] Erreur : {e}")
        return {"succes": False, "erreur": str(e)}