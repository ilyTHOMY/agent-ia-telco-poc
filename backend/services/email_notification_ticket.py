import os
from datetime import datetime, timezone

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_DISPONIBLE = True
except ImportError:
    SENDGRID_DISPONIBLE = False


def envoyer_email_ticket(ticket: dict) -> dict:
    """
    Envoie un email de notification quand un ticket est crée
    Appelé automatiquement par crm_api
    """
    api_key = os.getenv("SENDGRID_API_KEY", "")
    destinataire = os.getenv("EMAIL_DESTINATAIRE", "")
    expediteur = os.getenv("EMAIL_EXPEDITEUR", "")

    if not api_key or not destinataire or not expediteur:
        print("[EMAIL] SendGrid non configure — email non envoye.")
        print("[EMAIL] Ajoute SENDGRID_API_KEY, EMAIL_DESTINATAIRE, EMAIL_EXPEDITEUR dans .env")
        return {"succes": False, "raison": "non_configure"}

    if not SENDGRID_DISPONIBLE:
        print("[EMAIL] sendgrid non installe — pip install sendgrid")
        return {"succes": False, "raison": "sendgrid_non_installe"}

    priorite = ticket.get("priorite", "P3")
    type_rec = ticket.get("type_reclamation", "inconnu").replace("_", " ")
    telephone = ticket.get("telephone", "—")
    id_ticket = ticket.get("id", "—")
    canal = ticket.get("canal_origine", "—")
    description = ticket.get("description", "—")[:300]
    sla = ticket.get("sla_heures", 24)
    date = ticket.get("date_ouverture", datetime.now(timezone.utc).isoformat())[:19].replace("T", " ")

    emoji_prio = "🚨" if priorite == "P1" else "⚠️" if priorite == "P2" else "📋"

    sujet = f"{emoji_prio} [{priorite}] Nouveau ticket {id_ticket} — {type_rec}"

    corps_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#f8f9fa;padding:20px;border-radius:10px">

      <div style="background:{'#dc2626' if priorite=='P1' else '#d97706' if priorite=='P2' else '#2563eb'};
                  color:white;padding:16px 20px;border-radius:8px 8px 0 0;">
        <h2 style="margin:0;font-size:18px">{emoji_prio} Nouveau ticket — Priorite {priorite}</h2>
        <p style="margin:4px 0 0;opacity:.85;font-size:13px">Agent IA Support Mobile Money UEMOA</p>
      </div>

      <div style="background:white;padding:20px;border-radius:0 0 8px 8px;border:1px solid #e5e7eb">

        <table style="width:100%;border-collapse:collapse;font-size:14px">
          <tr style="border-bottom:1px solid #f3f4f6">
            <td style="padding:8px;color:#6b7280;font-weight:600;width:35%">Reference</td>
            <td style="padding:8px;font-family:monospace;color:#1d4ed8;font-weight:700">{id_ticket}</td>
          </tr>
          <tr style="border-bottom:1px solid #f3f4f6">
            <td style="padding:8px;color:#6b7280;font-weight:600">Type</td>
            <td style="padding:8px;color:#111827;text-transform:capitalize">{type_rec}</td>
          </tr>
          <tr style="border-bottom:1px solid #f3f4f6">
            <td style="padding:8px;color:#6b7280;font-weight:600">Telephone client</td>
            <td style="padding:8px;font-family:monospace">{telephone}</td>
          </tr>
          <tr style="border-bottom:1px solid #f3f4f6">
            <td style="padding:8px;color:#6b7280;font-weight:600">Canal</td>
            <td style="padding:8px">{canal}</td>
          </tr>
          <tr style="border-bottom:1px solid #f3f4f6">
            <td style="padding:8px;color:#6b7280;font-weight:600">SLA</td>
            <td style="padding:8px;color:{'#dc2626' if sla<=1 else '#d97706' if sla<=4 else '#059669'};font-weight:600">
              {sla} heure(s)
            </td>
          </tr>
          <tr style="border-bottom:1px solid #f3f4f6">
            <td style="padding:8px;color:#6b7280;font-weight:600">Date ouverture</td>
            <td style="padding:8px">{date}</td>
          </tr>
          <tr>
            <td style="padding:8px;color:#6b7280;font-weight:600;vertical-align:top">Description</td>
            <td style="padding:8px;color:#374151;line-height:1.5">{description}</td>
          </tr>
        </table>

        <div style="margin-top:20px;padding:12px;background:#f3f4f6;border-radius:6px;font-size:12px;color:#6b7280">
          Dashboard : <a href="http://localhost:3000/pages/dashboard.html" style="color:#2563eb">Voir le dashboard</a>
          &nbsp;|&nbsp;
          Rapport PDF : <a href="http://localhost:8000/api/v1/rapports/{id_ticket}/pdf" style="color:#2563eb">Telecharger</a>
        </div>

      </div>

      <p style="text-align:center;color:#9ca3af;font-size:11px;margin-top:12px">
        Agent IA Support Telco — Mobile Money UEMOA · Dakar, Senegal
      </p>
    </div>
    """

    try:
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        message = Mail(
            from_email=Email(expediteur, "Agent IA Support"),
            to_emails=To(destinataire),
            subject=sujet,
            html_content=Content("text/html", corps_html),
        )
        response = sg.client.mail.send.post(request_body=message.get())

        if response.status_code in (200, 202):
            print(f"[EMAIL] Email envoye pour {id_ticket} → {destinataire}")
            return {"succes": True, "id_ticket": id_ticket, "destinataire": destinataire}
        else:
            print(f"[EMAIL] Erreur SendGrid : {response.status_code}")
            return {"succes": False, "raison": f"status_{response.status_code}"}

    except Exception as e:
        print(f"[EMAIL] Exception : {e}")
        return {"succes": False, "raison": str(e)}
