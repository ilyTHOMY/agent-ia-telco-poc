"""
Mock API Mobile Money — simule les API Wave, Orange Money, Mixx by Yas.
En production, remplacer par les vrais endpoints operateurs.
Utilise par l'orchestrateur IA et les routes FastAPI.
"""
import json
import random
from pathlib import Path
from datetime import datetime, timezone

DONNEES_DIR = Path(__file__).parent.parent.parent / "data"


def _charger_clients() -> list:
    with open(DONNEES_DIR / "clients.json", encoding="utf-8") as f:
        return json.load(f)["clients"]


def _charger_transactions() -> list:
    with open(DONNEES_DIR / "transactions.json", encoding="utf-8") as f:
        return json.load(f)["transactions"]


def _horodatage() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Clients ────────────────────────────────────────────────────────────────────

def obtenir_client_par_telephone(telephone: str) -> dict | None:
    """Retourne le profil complet d'un client via son numero."""
    for client in _charger_clients():
        if client["telephone"] == telephone:
            return client
    return None


def obtenir_solde(telephone: str) -> dict:
    """Retourne le solde et les plafonds du compte."""
    client = obtenir_client_par_telephone(telephone)
    if not client:
        return {"succes": False, "erreur": "Client introuvable"}
    return {
        "succes": True,
        "telephone": telephone,
        "operateur": client["operateur"],
        "solde_xof": client["solde_xof"],
        "plafond_journalier_xof": client["plafond_journalier_xof"],
        "plafond_mensuel_xof": client["plafond_mensuel_xof"],
        "statut_compte": client["statut_compte"],
        "horodatage": _horodatage(),
    }


def verifier_statut_compte(telephone: str) -> dict:
    """Retourne le statut KYC et les signalements actifs."""
    client = obtenir_client_par_telephone(telephone)
    if not client:
        return {"succes": False, "erreur": "Client introuvable"}
    return {
        "succes": True,
        "telephone": telephone,
        "operateur": client["operateur"],
        "statut_compte": client["statut_compte"],
        "statut_kyc": client["statut_kyc"],
        "signalements": client["signalements"],
        "tentatives_pin_echouees": client["tentatives_pin_echouees"],
        "segment": client["segment"],
        "langue": client["langue"],
    }


def bloquer_compte(telephone: str, motif: str) -> dict:
    """Bloque un compte en urgence (fraude / SIM swap)."""
    client = obtenir_client_par_telephone(telephone)
    if not client:
        return {"succes": False, "erreur": "Client introuvable"}
    return {
        "succes": True,
        "telephone": telephone,
        "action": "compte_bloque",
        "motif": motif,
        "horodatage": _horodatage(),
        "message": f"Compte {telephone} bloque. Equipe securite notifiee.",
    }


# ── Transactions ───────────────────────────────────────────────────────────────

def obtenir_statut_transaction(reference: str) -> dict:
    """Retourne le statut d'une transaction par reference."""
    for txn in _charger_transactions():
        if txn["reference"] == reference or txn["id"] == reference:
            return {"succes": True, "transaction": txn}
    return {"succes": False, "erreur": "Transaction introuvable"}


def obtenir_historique_transactions(telephone: str, limite: int = 5) -> dict:
    """Retourne les dernieres transactions d'un client."""
    client = obtenir_client_par_telephone(telephone)
    if not client:
        return {"succes": False, "erreur": "Client introuvable"}
    txns = [
        t for t in _charger_transactions()
        if t.get("telephone_expediteur") == telephone
        or t.get("telephone_beneficiaire") == telephone
    ]
    txns.sort(key=lambda t: t["date_initiation"], reverse=True)
    return {
        "succes": True,
        "telephone": telephone,
        "transactions": txns[:limite],
        "total": len(txns),
    }


def declencher_remboursement(id_transaction: str) -> dict:
    """Declenche un remboursement pour une transaction eligible."""
    for txn in _charger_transactions():
        if txn["id"] == id_transaction:
            if not txn.get("remboursement_eligible"):
                return {"succes": False, "erreur": "Transaction non eligible au remboursement"}
            if txn.get("statut_remboursement") == "rembourse":
                return {"succes": False, "erreur": "Transaction deja remboursee"}
            ref_remb = f"RMB-{id_transaction[-6:]}-{random.randint(1000, 9999)}"
            return {
                "succes": True,
                "id_transaction": id_transaction,
                "montant_rembourse_xof": txn["montant_xof"],
                "statut_remboursement": "en_cours",
                "delai_estime": "2 a 4 heures",
                "reference_remboursement": ref_remb,
                "horodatage": _horodatage(),
            }
    return {"succes": False, "erreur": "Transaction introuvable"}
