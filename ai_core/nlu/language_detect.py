"""
Detection de langue — identifie si le message est en francais,
en wolof ou en melange franco-wolof.
Pas de librairie externe : approche par mots-cles et heuristiques.
"""

MOTS_WOLOF = {
    "sama", "bi", "bu", "la", "na", "da", "di", "dafa", "dama",
    "waaye", "xaalis", "compte", "kalpae", "jox", "dem", "nekk",
    "fan", "naka", "bari", "amul", "am", "man", "moo", "luy",
    "fi", "ko", "ci", "ak", "te", "ndax", "wante", "yow",
    "jend", "yonni", "joge", "seede", "yem", "soppaliku",
    "salaam", "aleekum", "nga", "def", "maa", "ngi", "jaam",
    "togg", "xam", "woon", "add", "set", "doo", "du",
}

MOTS_FRANCAIS = {
    "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
    "mon", "ma", "mes", "ton", "ta", "son", "sa", "le", "la",
    "les", "un", "une", "des", "et", "ou", "mais", "donc",
    "bonjour", "merci", "aide", "compte", "transfert", "argent",
    "solde", "retrait", "depot", "facture", "fraude", "bloque",
    "comment", "pourquoi", "quand", "combien", "quel", "quelle",
    "pas", "pas", "non", "oui", "bien", "mal", "veux", "vouloir",
}

SEUIL_WOLOF = 0.15


def detecter_langue(message: str) -> dict:
    """
    Detecte la langue du message.
    Retourne : {"langue": "fr"|"wo"|"fr-wo", "confiance": float}
    """
    if not message or not message.strip():
        return {"langue": "fr", "confiance": 1.0}

    mots = message.lower().split()
    total = len(mots)
    if total == 0:
        return {"langue": "fr", "confiance": 1.0}

    nb_wolof = sum(1 for m in mots if m in MOTS_WOLOF)
    nb_fr = sum(1 for m in mots if m in MOTS_FRANCAIS)

    ratio_wo = nb_wolof / total
    ratio_fr = nb_fr / total

    if ratio_wo >= 0.5:
        return {"langue": "wo", "confiance": round(ratio_wo, 2)}
    elif ratio_wo >= SEUIL_WOLOF and ratio_fr >= SEUIL_WOLOF:
        return {"langue": "fr-wo", "confiance": round((ratio_wo + ratio_fr) / 2, 2)}
    else:
        return {"langue": "fr", "confiance": round(max(ratio_fr, 0.7), 2)}


def adapter_langue_reponse(langue: str) -> str:
    """
    Retourne l'instruction de langue a injecter dans le prompt Gemini.
    """
    if langue == "wo":
        return (
            "Reponds UNIQUEMENT en wolof. "
            "Utilise un wolof simple et courant, pas trop formel. "
            "Si tu ne sais pas traduire un terme technique (comme 'transaction', 'KYC'), "
            "garde-le en francais."
        )
    elif langue == "fr-wo":
        return (
            "Le client parle en melange francais-wolof (franco-wolof). "
            "Reponds en francais mais avec naturel, tu peux utiliser quelques mots wolof "
            "courants comme 'waaye' (mais), 'ndax' (parce que), 'dafa' si c'est naturel. "
            "Ne force pas le wolof."
        )
    else:
        return "Reponds en francais clair et simple."
