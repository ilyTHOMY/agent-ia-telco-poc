import json
import random
import uuid
from pathlib import Path
from datetime import datetime, timezone

DONNEES_DIR = Path(__file__).parent.parent.parent / "data"
MAX_TENTATIVES_PIN = 3

# Valeurs par defaut BCEAO pour nouveau client (compte non verifie niveau 1)
DEFAUTS_NOUVEAU_CLIENT = {
    "statut_compte": "actif",
    "solde_xof": 0,
    "plafond_journalier_xof": 100000,   # Limite BCEAO niveau 1
    "plafond_mensuel_xof": 300000,
    "total_transactions_30j": 0,
    "tentatives_pin_echouees": 0,
}


def _charger(fichier: str) -> dict | list:
    chemin = DONNEES_DIR / fichier
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def _sauvegarder(fichier: str, donnees: dict | list) -> None:
    chemin = DONNEES_DIR / fichier
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)


def _horodatage() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Auth & Clients ─────────────────────────────────────────────────────────────

def obtenir_client_par_telephone(telephone: str) -> dict | None:
    data = _charger("clients.json")
    clients = data if isinstance(data, list) else data.get("clients", [])
    return next((c for c in clients if c["telephone"] == telephone), None)


def verifier_pin(telephone: str, pin: str) -> dict:
    """
    Verifie le PIN. Si le client n'existe pas, cree un profil temporaire
    """
    client = obtenir_client_par_telephone(telephone)

    # Nouveau client 
    if not client:
        # Detecter l'operateur via le prefixe du numero
        operateur = _detecter_operateur(telephone)

        nouveau = {
            "id": f"CUST-{operateur.upper()[:4]}-{str(uuid.uuid4())[:8].upper()}",
            "operateur": operateur,
            "telephone": telephone,
            "nom": "Nouveau client",
            "pin": str(pin),
            "date_creation": _horodatage(),
            "derniere_activite": _horodatage(),
            **DEFAUTS_NOUVEAU_CLIENT,
        }

        # Sauvegarder dans clients.json
        try:
            data = _charger("clients.json")
            if isinstance(data, dict):
                data["clients"].append(nouveau)
            else:
                data.append(nouveau)
            _sauvegarder("clients.json", data)
        except Exception as e:
            print(f"[AUTH] Erreur sauvegarde nouveau client : {e}")

        return {
            "succes": True,
            "bloque": False,
            "nouveau_client": True,
            "client": nouveau,
            "message": "Compte cree. Vos limites seront etendues apres verification d'identite (KYC).",
        }

    # Client existant 
    if client.get("statut_compte") == "bloque":
        return {"succes": False, "erreur": "Compte bloque. Contactez votre operateur.", "bloque": True}

    tentatives = client.get("tentatives_pin_echouees", 0)
    if tentatives >= MAX_TENTATIVES_PIN:
        return {"succes": False, "erreur": "Compte bloque apres 3 tentatives.", "bloque": True}

    if str(pin) != str(client.get("pin", "")):
        restantes = MAX_TENTATIVES_PIN - tentatives - 1
        # Incrementer tentatives dans le JSON
        _incrementer_tentatives_pin(telephone)
        return {
            "succes": False,
            "erreur": f"PIN incorrect. {restantes} tentative(s) restante(s).",
            "bloque": restantes <= 0,
            "tentatives_restantes": restantes,
        }

    # Reinitialiser compteur tentatives si connexion reussie
    _reset_tentatives_pin(telephone)

    return {
        "succes": True,
        "bloque": False,
        "nouveau_client": False,
        "client": client,
    }


def _detecter_operateur(telephone: str) -> str:
    """Detecte l'operateur Senegalais selon le prefixe."""
    t = telephone.replace("+221", "").replace("00221", "")
    if t.startswith(("77", "78")):
        return "wave"
    elif t.startswith(("76", "77")):
        return "orange_money"
    elif t.startswith("76"):
        return "mixx_by_yas"
    return "wave"  # Par defaut


def _incrementer_tentatives_pin(telephone: str) -> None:
    try:
        data = _charger("clients.json")
        clients = data if isinstance(data, list) else data.get("clients", [])
        for c in clients:
            if c["telephone"] == telephone:
                c["tentatives_pin_echouees"] = c.get("tentatives_pin_echouees", 0) + 1
                break
        _sauvegarder("clients.json", data)
    except Exception:
        pass


def _reset_tentatives_pin(telephone: str) -> None:
    try:
        data = _charger("clients.json")
        clients = data if isinstance(data, list) else data.get("clients", [])
        for c in clients:
            if c["telephone"] == telephone:
                c["tentatives_pin_echouees"] = 0
                c["derniere_activite"] = _horodatage()
                break
        _sauvegarder("clients.json", data)
    except Exception:
        pass


def mettre_a_jour_nom_client(telephone: str, nom: str) -> None:
    """Permet au nouveau client de renseigner son nom en cours de conversation."""
    try:
        data = _charger("clients.json")
        clients = data if isinstance(data, list) else data.get("clients", [])
        for c in clients:
            if c["telephone"] == telephone:
                c["nom"] = nom
                break
        _sauvegarder("clients.json", data)
    except Exception:
        pass


def bloquer_compte(telephone: str, motif: str) -> dict:
    try:
        data = _charger("clients.json")
        clients = data if isinstance(data, list) else data.get("clients", [])
        for c in clients:
            if c["telephone"] == telephone:
                c["statut_compte"] = "bloque"
                break
        _sauvegarder("clients.json", data)
    except Exception:
        pass
    return {
        "succes": True, "telephone": telephone, "action": "compte_bloque",
        "motif": motif, "horodatage": _horodatage(),
    }


# Solde & Statut 

def obtenir_solde(telephone: str) -> dict:
    client = obtenir_client_par_telephone(telephone)
    if not client:
        return {"succes": False, "erreur": "Client introuvable"}
    return {
        "succes": True,
        "telephone": telephone,
        "operateur": client.get("operateur", "inconnu"),
        "solde_xof": client.get("solde_xof", 0),
        "plafond_journalier_xof": client.get("plafond_journalier_xof", 100000),
        "plafond_mensuel_xof": client.get("plafond_mensuel_xof", 300000),
        "statut_compte": client.get("statut_compte", "actif"),
        "horodatage": _horodatage(),
    }


def verifier_statut_compte(telephone: str) -> dict:
    client = obtenir_client_par_telephone(telephone)
    if not client:
        return {"succes": False, "erreur": "Client introuvable"}
    return {
        "succes": True,
        "telephone": telephone,
        "operateur": client.get("operateur"),
        "statut_compte": client.get("statut_compte", "actif"),
        "tentatives_pin_echouees": client.get("tentatives_pin_echouees", 0),
    }


# Transactions 

def obtenir_statut_transaction(reference: str) -> dict:
    data = _charger("transactions.json")
    txns = data if isinstance(data, list) else data.get("transactions", [])
    for txn in txns:
        if txn.get("reference") == reference or txn.get("id") == reference:
            return {"succes": True, "transaction": txn}
    return {"succes": False, "erreur": "Transaction introuvable"}


def obtenir_historique_transactions(telephone: str, limite: int = 5) -> dict:
    data = _charger("transactions.json")
    txns = data if isinstance(data, list) else data.get("transactions", [])
    filtres = [
        t for t in txns
        if t.get("telephone_expediteur") == telephone
        or t.get("telephone_beneficiaire") == telephone
    ]
    filtres.sort(key=lambda t: t.get("date_initiation", ""), reverse=True)
    return {"succes": True, "telephone": telephone, "transactions": filtres[:limite], "total": len(filtres)}


def declencher_remboursement(id_transaction: str) -> dict:
    data = _charger("transactions.json")
    txns = data if isinstance(data, list) else data.get("transactions", [])
    for txn in txns:
        if txn.get("id") == id_transaction:
            if not txn.get("remboursement_eligible"):
                return {"succes": False, "erreur": "Transaction non eligible au remboursement"}
            if txn.get("statut_remboursement") == "rembourse":
                return {"succes": False, "erreur": "Transaction deja remboursee"}
            ref = f"RMB-{id_transaction[-6:]}-{random.randint(1000,9999)}"
            txn["statut_remboursement"] = "en_cours"
            _sauvegarder("transactions.json", data)
            return {
                "succes": True,
                "id_transaction": id_transaction,
                "montant_rembourse_xof": txn["montant_xof"],
                "statut_remboursement": "en_cours",
                "delai_estime": "2 a 4 heures",
                "reference_remboursement": ref,
                "horodatage": _horodatage(),
            }
    return {"succes": False, "erreur": "Transaction introuvable"}
