"""
Retriever v2 — plus rapide :
- Modele embedding charge UNE SEULE FOIS au demarrage (singleton)
- Cache des resultats frequents en memoire
- Fallback gracieux si Qdrant indisponible
"""
import os
from functools import lru_cache
from typing import Optional

# Singleton pour le modele embedding — charge une seule fois
_modele_embedding = None
_qdrant_client = None


def _get_modele():
    global _modele_embedding
    if _modele_embedding is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("[RAG] Chargement modele embedding...")
            _modele_embedding = SentenceTransformer(
                os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
            )
            print("[RAG] Modele embedding pret.")
        except Exception as e:
            print(f"[RAG] Impossible de charger le modele : {e}")
            _modele_embedding = None
    return _modele_embedding


def _get_qdrant():
    global _qdrant_client
    if _qdrant_client is None:
        try:
            from qdrant_client import QdrantClient
            host = os.getenv("QDRANT_HOST", "qdrant")
            port = int(os.getenv("QDRANT_PORT", "6333"))
            _qdrant_client = QdrantClient(host=host, port=port, timeout=3)
            print(f"[RAG] Qdrant connecte : {host}:{port}")
        except Exception as e:
            print(f"[RAG] Qdrant indisponible : {e}")
            _qdrant_client = None
    return _qdrant_client


# Cache simple en memoire pour les requetes frequentes
_cache_requetes: dict[str, str] = {}
MAX_CACHE = 100


def recuperer_contexte(
    message: str,
    operateur: str = None,
    top_k: int = 2,
) -> str:
    """
    Recherche semantique dans Qdrant.
    Retourne les chunks FAQ les plus pertinents.
    top_k=2 par defaut (plus rapide que 3).
    Cache les resultats pour les questions frequentes.
    """
    # Cle de cache
    cle_cache = f"{message[:80]}_{operateur}_{top_k}"
    if cle_cache in _cache_requetes:
        return _cache_requetes[cle_cache]

    modele = _get_modele()
    client = _get_qdrant()

    if not modele or not client:
        return _fallback_faq(message, operateur)

    try:
        # Encoder le message
        vecteur = modele.encode(message).tolist()

        # Filtrer par operateur si specifie
        filtre = None
        if operateur:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            filtre = Filter(
                must=[FieldCondition(
                    key="operateur",
                    match=MatchValue(value=operateur)
                )]
            )
        # filtre = None Pour du debuggong
        
        # Recherche dans Qdrant
        collection = os.getenv("QDRANT_COLLECTION", "faq_mobile_money")
        print(f"[RAG DEBUG] Query='{message}' operateur='{operateur}' collection='{collection}'")
        resultats = client.search(
            collection_name=collection,
            query_vector=vecteur,
            limit=top_k,
            query_filter=filtre,
            score_threshold=0.15,  # Ignorer les resultats peu pertinents
        )
        print(f"[RAG DEBUG] Nb resultats: {len(resultats)}")
        for r in resultats:
            print(f"[RAG DEBUG] Score={r.score:.3f} source={r.payload.get('source','')}")

        if not resultats:
            return _fallback_faq(message, operateur)

        chunks = []
        for r in resultats:
            source = r.payload.get("source", "")
            texte = r.payload.get("contenu", "") or r.payload.get("texte", "")
            if texte:
                chunks.append(f"[{source}] {texte}")

        contexte = "\n\n".join(chunks)

        # Mettre en cache
        if len(_cache_requetes) < MAX_CACHE:
            _cache_requetes[cle_cache] = contexte

        return contexte

    except Exception as e:
        print(f"[RAG] Erreur recherche : {e}")
        return _fallback_faq(message, operateur)


def _fallback_faq(message: str, operateur: str = None) -> str:
    """
    Fallback si Qdrant indisponible.
    Retourne des informations de base selon les mots cles du message.
    """
    msg = message.lower()

    # Frais de base
    if any(mot in msg for mot in ["frais", "tarif", "cout", "combien", "taxation"]):
        if operateur == "wave" or "wave" in msg:
            return "Wave : transfert 1% (max 5 000 XOF). Depot gratuit. Retrait 1%."
        if operateur == "orange_money" or "orange" in msg:
            return "Orange Money : transfert 0.8%. Depot et retrait gratuits."
        if operateur == "mixx" or "mixx" in msg:
            return "Mixx : transfert Mixx-Mixx gratuit. Retrait 0.8%."
        return "Frais variables selon l'operateur (0.8% a 1%). Le depot est toujours gratuit."

    # Limites
    if any(mot in msg for mot in ["limite", "plafond", "maximum", "max"]):
        return "Limite journaliere : 500 000 XOF (compte verifie). 100 000 XOF (non verifie). Mensuel : 2 000 000 XOF."

    # PIN
    if any(mot in msg for mot in ["pin", "code", "mot de passe", "oublie"]):
        return "Pour reinitialiser le PIN : ouvrir l'application > PIN oublie > entrer le numero > recevoir OTP > nouveau PIN."

    # Compte bloque
    if any(mot in msg for mot in ["bloque", "suspendu", "acceder"]):
        return "Compte bloque apres 3 tentatives PIN incorrectes. Contacter le support : Wave 3330, Orange Money 888, Mixx 3232."

    return ""


def vider_cache():
    """Vide le cache des requetes (utile apres reindexation)."""
    global _cache_requetes
    _cache_requetes = {}
    print("[RAG] Cache vide.")


def reinitialiser_connexions():
    """Force la reconnexion a Qdrant et rechargement du modele."""
    global _modele_embedding, _qdrant_client
    _modele_embedding = None
    _qdrant_client = None
    vider_cache()
    print("[RAG] Connexions reinitialiseees.")
