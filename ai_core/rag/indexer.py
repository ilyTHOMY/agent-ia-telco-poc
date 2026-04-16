"""
Indexer — script de vectorisation de la base de connaissances.
A executer une seule fois au demarrage ou apres mise a jour des FAQ.
Lance via : python -m ai_core.rag.indexer
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_core.rag.knowledge_base import charger_tous_documents
from ai_core.rag.vector_store import indexer_documents, vider_collection


def indexer_base_de_connaissances(reinitialiser: bool = False) -> int:
    """
    Charge tous les documents FAQ et les indexe dans Qdrant.
    Si reinitialiser=True, vide la collection avant d'indexer.
    """
    print("[RAG] Demarrage de l'indexation...")

    if reinitialiser:
        print("[RAG] Reinitialisation de la collection...")
        vider_collection()

    documents = charger_tous_documents()
    if not documents:
        print("[RAG] Aucun document trouve. Verifier le dossier ai_core/rag/docs/")
        return 0

    nb_indexes = indexer_documents(documents)
    print(f"[RAG] Indexation terminee : {nb_indexes} chunks dans Qdrant.")
    return nb_indexes


if __name__ == "__main__":
    reinit = "--reinit" in sys.argv
    indexer_base_de_connaissances(reinitialiser=reinit)
