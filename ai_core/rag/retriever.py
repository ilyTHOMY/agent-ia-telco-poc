"""
Retriever — recupere les chunks pertinents depuis Qdrant et les formate pour injection dans le prompt Gemini.
Gere le fallback sur la recherche par mots-cles si Qdrant est indisponible.
"""
from ai_core.rag.knowledge_base import charger_tous_documents, rechercher_sections_pertinentes

_documents_cache: list[dict] = []


def _get_documents_cache() -> list[dict]:
    global _documents_cache
    if not _documents_cache:
        _documents_cache = charger_tous_documents()
    return _documents_cache


def recuperer_contexte(
    query: str,
    operateur: str = None,
    top_k: int = 3,
) -> str:
    """
    Recupere les chunks les plus pertinents pour une query.
    Tente d'abord Qdrant, fallback sur recherche par mots-cles.
    Retourne le contexte formate pour injection dans le prompt Gemini.
    """
    try:
        from ai_core.rag.vector_store import rechercher
        chunks = rechercher(query, top_k=top_k, operateur=operateur)

        if not chunks:
            raise ValueError("Aucun resultat Qdrant")

    except Exception as e:
        print(f"[RAG] Qdrant indisponible ({e}), fallback mots-cles")
        docs = _get_documents_cache()
        chunks = rechercher_sections_pertinentes(query, docs, top_k=top_k)
        chunks = [{"contenu": c["contenu"], "source": c["source"], "score": 0.0} for c in chunks]

    if not chunks:
        return ""

    contexte = "INFORMATIONS VERIFIEES ISSUES DE LA BASE DE CONNAISSANCES :\n\n"
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source", "unknown").replace(".md", "").replace("faq_", "").replace("_", " ")
        contexte += f"[{i}] Source : {source}\n"
        contexte += f"{chunk['contenu']}\n\n"

    contexte += (
        "IMPORTANT : Base tes reponses UNIQUEMENT sur ces informations verifiees. "
        "Si l'information n'est pas dans ce contexte, dis-le clairement "
        "et propose d'escalader vers un conseiller."
    )

    return contexte
