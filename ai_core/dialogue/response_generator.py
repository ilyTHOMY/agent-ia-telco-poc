import re


def nettoyer_reponse(texte: str) -> str:
    """Supprime les artefacts markdown non desires pour le chat."""
    # Garder les listes simples mais enlever les titres markdown
    texte = re.sub(r'^#{1,3}\s+', '', texte, flags=re.MULTILINE)
    # Enlever les blocs de code
    texte = re.sub(r'```.*?```', '', texte, flags=re.DOTALL)
    # Nettoyer les espaces multiples
    texte = re.sub(r'\n{3,}', '\n\n', texte)
    return texte.strip()


def enrichir_reponse(
    reponse: str,
    intention: str,
    entites: dict,
    client: dict = None,
    id_ticket: str = None,
) -> str:
    """
    Enrichit la reponse avec des elements contextuels pertinents.
    Ajoute la reference ticket, le numero de support selon l'operateur, etc.
    """
    reponse = nettoyer_reponse(reponse)

    # Ajouter reference ticket si present
    if id_ticket and id_ticket not in reponse:
        reponse += f"\n\nReference de votre dossier : **{id_ticket}**"

    # Ajouter numero support selon operateur
    if client and intention in ["transaction_non_recue", "retrait_echoue", "depot_non_credite", "fraude_suspectee"]:
        operateur = client.get("operateur", "")
        numeros = {
            "wave": "3330",
            "orange_money": "888",
            "mixx_by_yas": "3232",
        }
        numero = numeros.get(operateur)
        if numero and numero not in reponse:
            reponse += f"\n\nSupport {operateur.replace('_', ' ').title()} : **{numero}** (24h/24)"

    return reponse


def formater_pour_ussd(texte: str) -> str:
    """
    Adapte une reponse pour le canal USSD.
    Max 182 caracteres, pas d'accents, pas de markdown.
    """
    # Enlever accents
    remplacements = {
        'é':'e','è':'e','ê':'e','ë':'e',
        'à':'a','â':'a','ä':'a',
        'î':'i','ï':'i',
        'ô':'o','ö':'o',
        'ù':'u','û':'u','ü':'u',
        'ç':'c','É':'E','È':'E',
    }
    for src, dst in remplacements.items():
        texte = texte.replace(src, dst)

    # Enlever markdown
    texte = re.sub(r'\*+', '', texte)
    texte = re.sub(r'#{1,3}\s+', '', texte)

    # Tronquer si necessaire
    if len(texte) > 180:
        texte = texte[:177] + "..."

    return texte.strip()


def formater_pour_whatsapp(texte: str) -> str:
    """
    Adapte le texte pour WhatsApp — bold avec *asterisques* (natif WA).
    Gemini utilise **double** — convertir en simple.
    """
    texte = re.sub(r'\*\*(.+?)\*\*', r'*\1*', texte)
    return texte.strip()
