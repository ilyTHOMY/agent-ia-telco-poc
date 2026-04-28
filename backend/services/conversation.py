"""
Service conversation — persistance PostgreSQL des messages.
Wrappe le CRUD pour une utilisation simple depuis l'orchestrateur.
"""
from datetime import datetime, timezone
from backend.db.crud import sauvegarder_message_db, obtenir_historique_db


async def persister_message(
    db,
    id_session: str,
    telephone: str,
    role: str,
    contenu: str,
    canal: str = "chat",
    intention: str = None,
    sentiment: str = None,
    langue: str = None,
) -> None:
    """Sauvegarde un message en base PostgreSQL."""
    if db is None:
        return  # Mode sans BDD (PoC local sans PostgreSQL)
    try:
        await sauvegarder_message_db(db, {
            "id_session": id_session,
            "telephone": telephone,
            "canal": canal,
            "role": role,
            "contenu": contenu,
            "intention": intention,
            "sentiment": sentiment,
            "langue": langue,
            "horodatage": datetime.now(timezone.utc),
        })
    except Exception as e:
        print(f"[CONV] Erreur persistence message : {e}")


async def recuperer_historique(db, id_session: str, limite: int = 10) -> list[dict]:
    """Recupere l'historique depuis PostgreSQL."""
    if db is None:
        return []
    try:
        msgs = await obtenir_historique_db(db, id_session, limite=limite)
        return [{"role": m.role, "contenu": m.contenu} for m in msgs]
    except Exception as e:
        print(f"[CONV] Erreur recuperation historique : {e}")
        return []
