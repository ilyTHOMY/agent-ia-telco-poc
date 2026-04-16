"""
Vector Store — interface avec Qdrant pour le stockage et la recherche
des embeddings de la base de connaissances.
Utilise sentence-transformers pour generer les embeddings.
"""
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue,
)
from sentence_transformers import SentenceTransformer
from backend.config import settings

COLLECTION = settings.qdrant_collection
DIMENSION = 384  # dimension pour paraphrase-multilingual-MiniLM-L12-v2

_client: QdrantClient = None
_modele: SentenceTransformer = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
    return _client


def _get_modele() -> SentenceTransformer:
    """
    Charge le modele d'embedding multilingue.
    paraphrase-multilingual-MiniLM-L12-v2 supporte le francais,
    l'anglais et partiellement les langues africaines.
    """
    global _modele
    if _modele is None:
        print("[RAG] Chargement du modele d'embedding...")
        _modele = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        print("[RAG] Modele charge.")
    return _modele


def creer_collection() -> None:
    """Cree la collection Qdrant si elle n'existe pas."""
    client = _get_client()
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION not in collections:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=DIMENSION, distance=Distance.COSINE),
        )
        print(f"[RAG] Collection '{COLLECTION}' creee.")
    else:
        print(f"[RAG] Collection '{COLLECTION}' existante.")


def encoder_texte(texte: str) -> list[float]:
    """Genere l'embedding d'un texte."""
    modele = _get_modele()
    return modele.encode(texte).tolist()


def indexer_documents(documents: list[dict]) -> int:
    """
    Indexe une liste de documents dans Qdrant.
    Chaque document doit avoir : id, contenu, source, operateur.
    Retourne le nombre de documents indexes.
    """
    client = _get_client()
    creer_collection()

    points = []
    for i, doc in enumerate(documents):
        vecteur = encoder_texte(doc["contenu"])
        points.append(PointStruct(
            id=i,
            vector=vecteur,
            payload={
                "id_doc": doc["id"],
                "source": doc["source"],
                "operateur": doc["operateur"],
                "contenu": doc["contenu"],
            },
        ))

    client.upsert(collection_name=COLLECTION, points=points)
    print(f"[RAG] {len(points)} documents indexes dans Qdrant.")
    return len(points)


def rechercher(
    query: str,
    top_k: int = 3,
    operateur: str = None,
) -> list[dict]:
    """
    Recherche les chunks les plus pertinents pour une query.
    Filtre optionnel par operateur (wave, orange_money, mixx_by_yas).
    Retourne une liste de chunks avec leur score de similarite.
    """
    client = _get_client()
    vecteur_query = encoder_texte(query)

    filtre = None
    if operateur:
        filtre = Filter(
            must=[FieldCondition(
                key="operateur",
                match=MatchValue(value=operateur),
            )]
        )

    resultats = client.search(
        collection_name=COLLECTION,
        query_vector=vecteur_query,
        limit=top_k,
        query_filter=filtre,
    )

    return [
        {
            "contenu": r.payload["contenu"],
            "source": r.payload["source"],
            "operateur": r.payload["operateur"],
            "score": round(r.score, 3),
        }
        for r in resultats
    ]


def vider_collection() -> None:
    """Supprime et recrée la collection (pour reindexation complete)."""
    client = _get_client()
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION in collections:
        client.delete_collection(COLLECTION)
        print(f"[RAG] Collection '{COLLECTION}' supprimee.")
    creer_collection()
