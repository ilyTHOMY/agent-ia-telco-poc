"""
Mock USSD API — simule un agregateur USSD (type AfricasTalking).
Gere l'arbre de navigation USSD pour #144# (Orange Money) et #150# (Mixx).
Chaque session USSD est identifiee par un sessionId unique.
"""
from datetime import datetime, timezone

_sessions_ussd: dict = {}

MENU_PRINCIPAL = """Bienvenue Agent IA Mobile Money
1. Consulter mon solde
2. Signaler une transaction
3. Mon compte est bloque
4. Parler a un conseiller
5. Questions frequentes"""

MENU_TRANSACTION = """Type de probleme :
1. Transfert non recu
2. Retrait echoue
3. Depot non credite
4. Double debit
0. Retour"""

MENU_FAQ = """Questions frequentes :
1. Frais de transfert
2. Limites de transaction
3. Comment recharger
4. Horaires agents
0. Retour"""


def _horodatage() -> str:
    return datetime.now(timezone.utc).isoformat()


def traiter_requete_ussd(
    session_id: str,
    telephone: str,
    texte: str,
    code_service: str = "*144#",
) -> dict:
    """
    Traite une requete USSD et retourne la reponse.
    texte : chaine de navigation ex. "" (debut), "1", "1*2", "1*2*25000"
    """
    if session_id not in _sessions_ussd:
        _sessions_ussd[session_id] = {
            "session_id": session_id,
            "telephone": telephone,
            "code_service": code_service,
            "navigation": [],
            "debut": _horodatage(),
            "statut": "actif",
        }

    session = _sessions_ussd[session_id]
    session["navigation"].append(texte)

    etapes = [e for e in texte.split("*") if e] if texte else []

    if not etapes:
        reponse = f"CON {MENU_PRINCIPAL}"
    elif etapes[0] == "1":
        reponse = "END Consultation de votre solde en cours... Vous recevrez un SMS dans quelques secondes."
    elif etapes[0] == "2":
        if len(etapes) == 1:
            reponse = f"CON {MENU_TRANSACTION}"
        elif etapes[1] == "1":
            reponse = "END Votre signalement de transfert non recu est enregistre. Reference : TKT-USSD-001. Traitement sous 24h."
        elif etapes[1] == "2":
            reponse = "END Votre retrait echoue est signale. Un remboursement sera effectue si eligible."
        elif etapes[1] == "3":
            reponse = "END Depot non credite signale. Equipe reseau agents notifiee. Traitement sous 2h."
        elif etapes[1] == "4":
            reponse = "END Double debit detecte. Remboursement en cours. SMS de confirmation dans 30 min."
        elif etapes[1] == "0":
            reponse = f"CON {MENU_PRINCIPAL}"
        else:
            reponse = "END Option invalide. Reessayez."
    elif etapes[0] == "3":
        reponse = "END Votre demande de deblocage est enregistree. Un SMS avec les instructions vous sera envoye."
    elif etapes[0] == "4":
        reponse = "END Transfert vers un conseiller en cours... Votre numero de dossier : TKT-USSD-002. Rappel sous 5 min."
    elif etapes[0] == "5":
        if len(etapes) == 1:
            reponse = f"CON {MENU_FAQ}"
        elif etapes[1] == "1":
            reponse = "END Frais de transfert Wave : 0% (gratuit). Orange Money : 0.5% a 1%. Mixx : 0% pour les petits montants."
        elif etapes[1] == "2":
            reponse = "END Limite journaliere : 500 000 XOF. Limite mensuelle : 2 000 000 XOF (BCEAO)."
        elif etapes[1] == "3":
            reponse = "END Pour recharger : deposez de l'argent chez un agent agence ou par virement bancaire."
        elif etapes[1] == "4":
            reponse = "END Agents disponibles 7j/7 de 8h a 20h. Certains points ouverts 24h/24."
        elif etapes[1] == "0":
            reponse = f"CON {MENU_PRINCIPAL}"
        else:
            reponse = "END Option invalide."
    else:
        reponse = "END Option invalide. Composez *144# pour recommencer."

    if reponse.startswith("END"):
        session["statut"] = "termine"

    return {
        "succes": True,
        "session_id": session_id,
        "telephone": telephone,
        "reponse": reponse,
        "statut_session": session["statut"],
        "horodatage": _horodatage(),
    }


def obtenir_session_ussd(session_id: str) -> dict:
    """Retourne les details d'une session USSD."""
    session = _sessions_ussd.get(session_id)
    if not session:
        return {"succes": False, "erreur": "Session introuvable"}
    return {"succes": True, "session": session}


def lister_sessions_ussd() -> dict:
    """Retourne toutes les sessions USSD (pour le dashboard)."""
    return {
        "succes": True,
        "sessions": list(_sessions_ussd.values()),
        "total": len(_sessions_ussd),
    }
