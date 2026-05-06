import json
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from backend.mocks.crm_api import obtenir_ticket
from backend.mocks.mobile_money_api import obtenir_client_par_telephone, obtenir_statut_transaction

COULEUR_BLEU  = HexColor("#1D4ED8")
COULEUR_ROUGE = HexColor("#DC2626")
COULEUR_VERT  = HexColor("#059669")
COULEUR_GRIS  = HexColor("#F3F4F6")


def generer_rapport_pdf(id_ticket: str) -> bytes:
    """
    Genere un rapport d'incident PDF complet pour un ticket donne.
    Retourne les bytes du PDF.
    """
    res = obtenir_ticket(id_ticket)
    if not res["succes"]:
        raise ValueError(f"Ticket {id_ticket} introuvable")

    ticket = res["ticket"]
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    style_titre = ParagraphStyle("Titre", fontSize=18, textColor=COULEUR_BLEU,
                                  spaceAfter=20, alignment=TA_CENTER, fontName="Helvetica-Bold")
    style_section = ParagraphStyle("Section", fontSize=13, textColor=COULEUR_BLEU,
                                    spaceBefore=16, spaceAfter=8, fontName="Helvetica-Bold")
    style_corps = ParagraphStyle("Corps", fontSize=10, spaceAfter=6,
                                  leading=14, fontName="Helvetica")

    elements = []

    # En-tete
    elements.append(Paragraph("RAPPORT D'INCIDENT", style_titre))
    elements.append(Paragraph(f"Reference : {id_ticket}", ParagraphStyle(
        "Ref", fontSize=11, textColor=COULEUR_GRIS, alignment=TA_CENTER, fontName="Helvetica")))
    elements.append(Spacer(1, 0.5*cm))

    # Bandeau priorite
    priorite = ticket.get("priorite", "P3")
    couleur_priorite = COULEUR_ROUGE if priorite in ["P1"] else HexColor("#D97706") if priorite == "P2" else COULEUR_VERT
    tableau_entete = Table(
        [[f"PRIORITE {priorite}", ticket.get("statut", "").upper(), ticket.get("canal_origine", "").upper()]],
        colWidths=[5*cm, 5*cm, 5.5*cm],
    )
    tableau_entete.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), couleur_priorite),
        ("TEXTCOLOR", (0,0), (-1,-1), white),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [couleur_priorite]),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    elements.append(tableau_entete)
    elements.append(Spacer(1, 0.5*cm))

    # Informations principales
    elements.append(Paragraph("Informations du ticket", style_section))
    donnees_ticket = [
        ["Champ", "Valeur"],
        ["ID Ticket", id_ticket],
        ["Type reclamation", ticket.get("type_reclamation", "-")],
        ["Date ouverture", ticket.get("date_ouverture", "-")[:19].replace("T", " ")],
        ["SLA", f"{ticket.get('sla_heures', 24)} heures"],
        ["Canal d'origine", ticket.get("canal_origine", "-")],
        ["Agent assigne", ticket.get("agent_assigne") or "En attente"],
    ]
    if ticket.get("id_transaction"):
        donnees_ticket.append(["Transaction liee", ticket["id_transaction"]])

    tableau_ticket = Table(donnees_ticket, colWidths=[5*cm, 10.5*cm])
    tableau_ticket.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), COULEUR_BLEU),
        ("TEXTCOLOR", (0,0), (-1,0), white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,1), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [white, COULEUR_GRIS]),
        ("GRID", (0,0), (-1,-1), 0.5, HexColor("#D1D5DB")),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
    ]))
    elements.append(tableau_ticket)
    elements.append(Spacer(1, 0.4*cm))

    # Description
    elements.append(Paragraph("Description de l'incident", style_section))
    elements.append(Paragraph(ticket.get("description", "Non renseignee"), style_corps))
    elements.append(Spacer(1, 0.4*cm))

    # Historique des actions
    elements.append(Paragraph("Historique des actions", style_section))
    historique = ticket.get("historique", [])
    if historique:
        donnees_hist = [["Date", "Action", "Auteur", "Note"]]
        for h in historique:
            donnees_hist.append([
                h.get("date", "")[:19].replace("T", " "),
                h.get("action", "-"),
                h.get("auteur", "-"),
                (h.get("note", "") or "")[:60],
            ])
        tableau_hist = Table(donnees_hist, colWidths=[4*cm, 3*cm, 3*cm, 5.5*cm])
        tableau_hist.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), COULEUR_BLEU),
            ("TEXTCOLOR", (0,0), (-1,0), white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [white, COULEUR_GRIS]),
            ("GRID", (0,0), (-1,-1), 0.5, HexColor("#D1D5DB")),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
        ]))
        elements.append(tableau_hist)

    # Pied de page
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(
        f"Document genere automatiquement par l'Agent IA Support Telco — {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC",
        ParagraphStyle("Footer", fontSize=8, textColor=HexColor("#9CA3AF"), alignment=TA_CENTER)
    ))

    doc.build(elements)
    return buffer.getvalue()


def generer_rapport_json(id_ticket: str) -> dict:
    """Genere un rapport JSON structuré pour un ticket"""
    res = obtenir_ticket(id_ticket)
    if not res["succes"]:
        raise ValueError(f"Ticket {id_ticket} introuvable")
    ticket = res["ticket"]
    return {
        "rapport": {
            "id_ticket": id_ticket,
            "genere_le": datetime.now(timezone.utc).isoformat(),
            "ticket": ticket,
            "version_systeme": "2.0.0",
        }
    }