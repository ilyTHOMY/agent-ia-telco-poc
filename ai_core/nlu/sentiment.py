MOTS_FRUSTRATION = [
    "inacceptable", "scandaleux", "arnaque", "vol", "honte",
    "incompetent", "jamais", "toujours pareil", "marre", "ras le bol",
    "ridicule", "catastrophe", "aucun service", "fraude", "escroquerie",
    "nul", "deplorable", "inadmissible", "exaspere", "en colere",
    "revolte", "indigne", "choque", "furieux", "furie",
]

MOTS_NEGATIF = [
    "probleme", "bloque", "echoue", "pas recu", "perdu", "erreur",
    "bug", "marche pas", "fonctionne pas", "aide", "urgent",
    "impossible", "ne peut pas", "ne peux pas", "difficile",
    "inquiet", "inquiete", "perdu", "confus", "comprends pas",
]

MOTS_POSITIF = [
    "merci", "super", "parfait", "excellent", "bien", "genial",
    "top", "satisfait", "resolu", "ca marche", "nickel", "impeccable",
    "formidable", "bravo", "felicitations", "content", "contente",
]


def detecter_sentiment(message: str) -> str:
    """
    Detecte le sentiment du message.
    Retourne : 'positif' | 'neutre' | 'negatif' | 'frustre'
    L'ordre d'evaluation est important : positif > frustre > negatif > neutre.
    """
    if not message:
        return "neutre"

    msg = message.lower()

    if any(mot in msg for mot in MOTS_POSITIF):
        return "positif"

    if any(mot in msg for mot in MOTS_FRUSTRATION):
        return "frustre"

    if any(mot in msg for mot in MOTS_NEGATIF):
        return "negatif"

    return "neutre"


def adapter_ton_reponse(sentiment: str) -> str:
    """
    Retourne l'instruction de ton a injecter dans le prompt Gemini
    selon le sentiment detecte.
    """
    if sentiment == "frustre":
        return (
            "Le client est tres frustre ou en colere. "
            "Commence par reconnaitre sa frustration avec empathie. "
            "Sois bref, direct, et oriente immediatement vers une solution concrete. "
            "Ne dis pas 'Je comprends votre frustration' — montre-le en agissant vite."
        )
    elif sentiment == "negatif":
        return (
            "Le client est inquiet ou insatisfait. "
            "Sois rassurant, chaleureux et montre que tu prends sa demande au serieux. "
            "Propose une action concrete rapidement."
        )
    elif sentiment == "positif":
        return (
            "Le client est satisfait. "
            "Reste professionnel et chaleureux. "
            "Propose de l'aide supplementaire si besoin."
        )
    else:
        return (
            "Sois professionnel, clair et concis. "
            "Va droit au but."
        )
