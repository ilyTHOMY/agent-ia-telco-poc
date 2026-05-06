"""
Extraction d'entites — identifie les elements cles dans le message client.
Extrait : montants XOF, numeros de telephone, references de transactions, noms d'operateurs, fournisseurs de services.
"""
import re


# Patterns

PATTERN_MONTANT = re.compile(
    r"(\d[\d\s]*(?:\d{3})*)\s*(?:xof|fcfa|francs?|f\.?cfa|cfa)?",
    re.IGNORECASE,
)

PATTERN_TELEPHONE = re.compile(
    r"(?:\+221|00221|221)?[\s.-]?([7][0-9])[\s.-]?(\d{3})[\s.-]?(\d{2})[\s.-]?(\d{2})"
)

PATTERN_REFERENCE = re.compile(
    r"(?:WV|OM|MX|TXN|REF|INC)[-\s]?\d{4,}[-\w]*",
    re.IGNORECASE,
)

OPERATEURS = {
    "wave": ["wave"],
    "orange_money": ["orange money", "orange", "om"],
    "mixx_by_yas": ["mixx", "yas", "mixx by yas", "kalpae"],
}

FOURNISSEURS = {
    "SENELEC": ["senelec", "electricite", "lumiere", "courant"],
    "SEN_EAU": ["sen'eau", "seneau", "eau", "water"],
    "CANAL_PLUS": ["canal+", "canal plus", "canalsat"],
}


def extraire_montant(message: str) -> int | None:
    """Extrait le premier montant en XOF mentionne dans le message."""
    matches = PATTERN_MONTANT.findall(message)
    for match in matches:
        chiffres = re.sub(r"\s", "", match)
        try:
            valeur = int(chiffres)
            if valeur >= 100:
                return valeur
        except ValueError:
            continue
    return None


def extraire_telephone(message: str) -> str | None:
    """Extrait le premier numero de telephone senegalais dans le message."""
    match = PATTERN_TELEPHONE.search(message)
    if match:
        return f"+221{match.group(1)}{match.group(2)}{match.group(3)}{match.group(4)}"
    return None


def extraire_reference(message: str) -> str | None:
    """Extrait une reference de transaction dans le message."""
    match = PATTERN_REFERENCE.search(message)
    return match.group(0).upper() if match else None


def extraire_operateur(message: str) -> str | None:
    """Identifie l'operateur mentionne dans le message."""
    msg = message.lower()
    for operateur, mots_cles in OPERATEURS.items():
        if any(mot in msg for mot in mots_cles):
            return operateur
    return None


def extraire_fournisseur(message: str) -> str | None:
    """Identifie le fournisseur de service (SENELEC, SEN'EAU...) dans le message."""
    msg = message.lower()
    for fournisseur, mots_cles in FOURNISSEURS.items():
        if any(mot in msg for mot in mots_cles):
            return fournisseur
    return None


def extraire_entites(message: str) -> dict:
    """
    Extrait toutes les entites pertinentes d'un message client.
    Retourne un dict avec les entites trouvees (None si absente).
    """
    return {
        "montant_xof": extraire_montant(message),
        "telephone": extraire_telephone(message),
        "reference_transaction": extraire_reference(message),
        "operateur": extraire_operateur(message),
        "fournisseur": extraire_fournisseur(message),
    }
