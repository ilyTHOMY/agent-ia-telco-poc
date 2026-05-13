from pathlib import Path
from typing import Generator

DOCS_DIR = Path(__file__).parent / "docs"

CHUNK_SIZE = 400
CHUNK_OVERLAP = 80


def charger_document(chemin: Path) -> str:
    """Charge un fichier Markdown et retourne son contenu."""
    with open(chemin, encoding="utf-8") as f:
        return f.read()


def decouper_en_chunks(texte: str, taille: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """
    Decoupe un texte en chunks avec chevauchement.
    Essaie de couper aux fins de paragraphes pour preserver le sens.
    """
    chunks = []
    paragraphes = [p.strip() for p in texte.split("\n\n") if p.strip()]

    chunk_courant = ""
    for para in paragraphes:
        if len(chunk_courant) + len(para) <= taille:
            chunk_courant += "\n\n" + para if chunk_courant else para
        else:
            if chunk_courant:
                chunks.append(chunk_courant.strip())
            # Chevauchement : reprendre les derniers mots du chunk precedent
            mots = chunk_courant.split()
            overlap_text = " ".join(mots[-overlap // 5:]) if mots else ""
            chunk_courant = (overlap_text + "\n\n" + para).strip() if overlap_text else para

    if chunk_courant:
        chunks.append(chunk_courant.strip())

    return [
        {
            "contenu": chunk,
            "longueur": len(chunk),
            "index": i,
        }
        for i, chunk in enumerate(chunks)
    ]


def charger_tous_documents() -> list[dict]:
    """
    Charge tous les documents FAQ et les decoupe en chunks.
    Retourne une liste de chunks avec leurs metadonnees.
    """
    documents = []
    fichiers = list(DOCS_DIR.glob("*.md"))

    for fichier in fichiers:
        texte = charger_document(fichier)
        chunks = decouper_en_chunks(texte)
        operateur = fichier.stem.replace("faq_", "").replace("_", " ")

        for chunk in chunks:
            documents.append({
                "id": f"{fichier.stem}_{chunk['index']}",
                "source": fichier.name,
                "operateur": operateur,
                "contenu": chunk["contenu"],
                "longueur": chunk["longueur"],
            })

    print(f"[RAG] {len(documents)} chunks charges depuis {len(fichiers)} documents")
    return documents


def rechercher_sections_pertinentes(query: str, documents: list[dict], top_k: int = 3) -> list[dict]:
    """
    Recherche naive par mots-cles (fallback si Qdrant indisponible).
    En production, utiliser vector_store.rechercher() a la place.
    """
    query_mots = set(query.lower().split())
    scores = []

    for doc in documents:
        contenu_mots = set(doc["contenu"].lower().split())
        intersection = query_mots & contenu_mots
        score = len(intersection) / max(len(query_mots), 1)
        scores.append((score, doc))

    scores.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scores[:top_k] if _ > 0]
