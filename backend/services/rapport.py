import os
from pathlib import Path
from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from backend.mocks.crm_api import obtenir_ticket

# Couleurs
BLEU    = colors.HexColor('#4F6EFF')
TEAL    = colors.HexColor('#00D4B4')
ROUGE   = colors.HexColor('#FF5A65')
ORANGE  = colors.HexColor('#FF8C42')
VERT    = colors.HexColor('#00D97E')
OR      = colors.HexColor('#FFB830')
GRIS    = colors.HexColor('#8B92B8')
GRIS2   = colors.HexColor('#E8ECFF')
FOND    = colors.HexColor('#F8F9FF')
NOIR    = colors.HexColor('#1C2235')

PRIO_COULEURS = {
    'P1': ROUGE, 'P2': ORANGE, 'P3': BLEU, 'P4': GRIS
}
STATUT_COULEURS = {
    'ouvert': BLEU, 'en_cours': OR, 'resolu': VERT
}


def _styles():
    base = getSampleStyleSheet()
    return {
        'titre': ParagraphStyle('titre', fontSize=20, fontName='Helvetica-Bold',
            textColor=NOIR, spaceAfter=4),
        'sous_titre': ParagraphStyle('sous_titre', fontSize=11, fontName='Helvetica',
            textColor=GRIS, spaceAfter=12),
        'section': ParagraphStyle('section', fontSize=12, fontName='Helvetica-Bold',
            textColor=BLEU, spaceBefore=14, spaceAfter=6),
        'label': ParagraphStyle('label', fontSize=9, fontName='Helvetica-Bold',
            textColor=GRIS),
        'valeur': ParagraphStyle('valeur', fontSize=10, fontName='Helvetica',
            textColor=NOIR),
        'desc': ParagraphStyle('desc', fontSize=9, fontName='Helvetica',
            textColor=NOIR, leading=14),
        'msg_ia': ParagraphStyle('msg_ia', fontSize=9, fontName='Helvetica',
            textColor=NOIR, leading=13, leftIndent=8,
            backColor=colors.HexColor('#F0F4FF'),
            borderPad=6, borderRadius=4),
        'msg_client': ParagraphStyle('msg_client', fontSize=9, fontName='Helvetica',
            textColor=NOIR, leading=13, leftIndent=8,
            backColor=colors.HexColor('#F0FFF8'),
            borderPad=6, borderRadius=4),
        'heure': ParagraphStyle('heure', fontSize=7, fontName='Helvetica',
            textColor=GRIS, spaceAfter=2),
        'footer': ParagraphStyle('footer', fontSize=8, fontName='Helvetica',
            textColor=GRIS, alignment=TA_CENTER),
        'normal': base['Normal'],
    }


def generer_pdf(id_ticket: str, chemin_sortie: str = None) -> str:
    """
    Genere un rapport PDF complet pour un ticket.
    Retourne le chemin du fichier genere.
    """
    res = obtenir_ticket(id_ticket)
    if not res['succes']:
        raise ValueError(f"Ticket {id_ticket} introuvable")

    ticket = res['ticket']

    # Chemin de sortie
    if not chemin_sortie:
        dossier = Path('/tmp/rapports')
        dossier.mkdir(parents=True, exist_ok=True)
        chemin_sortie = str(dossier / f"rapport_{id_ticket}.pdf")

    doc = SimpleDocTemplate(
        chemin_sortie,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    st = _styles()
    elements = []

    # ── En-tete ───────────────────────────────────────────────────────────────
    prio = ticket.get('priorite', 'P3')
    couleur_prio = PRIO_COULEURS.get(prio, BLEU)

    header_data = [[
        Paragraph('<b>Agent IA Support</b><br/>Mobile Money UEMOA', st['valeur']),
        Paragraph(f'<b>RAPPORT DE TICKET</b><br/><font color="#4F6EFF">{id_ticket}</font>',
                  ParagraphStyle('h', fontSize=13, fontName='Helvetica-Bold',
                                 textColor=NOIR, alignment=TA_RIGHT)),
    ]]
    header_table = Table(header_data, colWidths=[9*cm, 8*cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,0), 1.5, BLEU),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.4*cm))

    # ── Bandeau priorite ──────────────────────────────────────────────────────
    statut = ticket.get('statut', 'ouvert')
    couleur_statut = STATUT_COULEURS.get(statut, BLEU)

    bandeau_data = [[
        Paragraph(f'Priorité : <b>{prio}</b>', ParagraphStyle('b1', fontSize=10,
            fontName='Helvetica-Bold', textColor=colors.white)),
        Paragraph(f'Statut : <b>{statut.replace("_"," ").upper()}</b>', ParagraphStyle('b2',
            fontSize=10, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_CENTER)),
        Paragraph(f'SLA : <b>{ticket.get("sla_heures",24)}h</b>', ParagraphStyle('b3',
            fontSize=10, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_RIGHT)),
    ]]
    bandeau = Table(bandeau_data, colWidths=[5.67*cm, 5.67*cm, 5.67*cm])
    bandeau.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), couleur_prio),
        ('BACKGROUND', (1,0), (1,0), couleur_statut),
        ('BACKGROUND', (2,0), (2,0), TEAL),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('ROUNDEDCORNERS', [6]),
    ]))
    elements.append(bandeau)
    elements.append(Spacer(1, 0.5*cm))

    # ── Informations ticket ───────────────────────────────────────────────────
    elements.append(Paragraph('Informations du ticket', st['section']))

    date_ouv = ticket.get('date_ouverture','')[:19].replace('T',' ')
    date_maj = ticket.get('date_mise_a_jour','')[:19].replace('T',' ')
    date_clo = ticket.get('date_cloture','')
    if date_clo:
        date_clo = date_clo[:19].replace('T',' ')

    infos = [
        ['Type de réclamation', ticket.get('type_reclamation','—').replace('_',' ').title()],
        ['Téléphone client', ticket.get('telephone','—')],
        ['Canal d\'origine', ticket.get('canal_origine','—')],
        ['Date d\'ouverture', date_ouv],
        ['Dernière mise à jour', date_maj],
        ['Date de clôture', date_clo or '—'],
        ['Agent assigné', ticket.get('agent_assigne') or '—'],
        ['ID Transaction', ticket.get('id_transaction') or '—'],
    ]

    info_table = Table(
        [[Paragraph(k, st['label']), Paragraph(str(v), st['valeur'])] for k,v in infos],
        colWidths=[5.5*cm, 11.5*cm]
    )
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), FOND),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,0), (-1,-2), 0.3, colors.HexColor('#E0E4F0')),
        ('ROUNDEDCORNERS', [4]),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.4*cm))

    # ── Description ───────────────────────────────────────────────────────────
    desc = ticket.get('description','')
    if desc:
        elements.append(Paragraph('Description', st['section']))
        elements.append(Paragraph(desc, st['desc']))
        elements.append(Spacer(1, 0.4*cm))

    # ── Historique conversation ───────────────────────────────────────────────
    historique_conv = ticket.get('historique_conversation', '')
    if historique_conv and historique_conv.strip():
        elements.append(Paragraph('Historique de la conversation', st['section']))
        elements.append(HRFlowable(width='100%', thickness=0.5, color=BLEU))
        elements.append(Spacer(1, 0.2*cm))

        lignes = historique_conv.strip().split('\n')
        for ligne in lignes:
            if not ligne.strip():
                elements.append(Spacer(1, 0.15*cm))
                continue
            if ligne.startswith('Client:'):
                texte = ligne[7:].strip()
                elements.append(Paragraph(f'👤 <b>Client</b>', st['heure']))
                elements.append(Paragraph(texte, st['msg_client']))
                elements.append(Spacer(1, 0.2*cm))
            elif ligne.startswith('Agent IA:'):
                texte = ligne[9:].strip()
                elements.append(Paragraph(f'🤖 <b>Agent IA</b>', st['heure']))
                elements.append(Paragraph(texte, st['msg_ia']))
                elements.append(Spacer(1, 0.2*cm))
            else:
                elements.append(Paragraph(ligne, st['desc']))

        elements.append(Spacer(1, 0.3*cm))

    # ── Historique actions ────────────────────────────────────────────────────
    historique = ticket.get('historique', [])
    if historique:
        elements.append(Paragraph('Historique des actions', st['section']))
        for action in historique:
            date_a = action.get('date','')[:19].replace('T',' ')
            auteur = action.get('auteur','—')
            note   = action.get('note','')
            acte   = action.get('action','').replace('_',' ')
            elements.append(Paragraph(
                f'<b>{date_a}</b> — {auteur} — {acte}',
                ParagraphStyle('ha', fontSize=8, fontName='Helvetica-Bold', textColor=GRIS)
            ))
            if note:
                elements.append(Paragraph(note, st['desc']))
            elements.append(Spacer(1, 0.15*cm))

    # ── CSAT ──────────────────────────────────────────────────────────────────
    csat = ticket.get('csat')
    if csat:
        elements.append(Paragraph('Évaluation client (CSAT)', st['section']))
        etoiles = '⭐' * csat.get('note', 0)
        commentaire = csat.get('commentaire','')
        elements.append(Paragraph(
            f'Note : <b>{etoiles} ({csat.get("note",0)}/5)</b>',
            st['valeur']
        ))
        if commentaire:
            elements.append(Paragraph(f'Commentaire : {commentaire}', st['desc']))
        elements.append(Spacer(1, 0.3*cm))

    # ── Footer ────────────────────────────────────────────────────────────────
    elements.append(HRFlowable(width='100%', thickness=0.5, color=GRIS))
    elements.append(Spacer(1, 0.2*cm))
    now = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    elements.append(Paragraph(
        f'Rapport généré le {now} · Agent IA Support Mobile Money UEMOA · Confidentiel',
        st['footer']
    ))

    doc.build(elements)
    return chemin_sortie

# Alias pour compatibilite avec routes_rapports.py
generer_rapport_pdf = generer_pdf

# Alias corrige — lit le fichier et retourne les bytes
def generer_rapport_pdf(id_ticket: str) -> bytes:
    chemin = generer_pdf(id_ticket)
    with open(chemin, 'rb') as f:
        return f.read()