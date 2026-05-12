"""
Routes auth — inscription nouveau client.
Separe de routes_chat pour plus de clarte.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from backend.mocks.mobile_money_api import obtenir_client_par_telephone
import json, uuid
from pathlib import Path
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["Auth"])

CLIENTS_FILE = Path(__file__).parent.parent.parent / "data" / "clients.json"

class DemandeInscription(BaseModel):
    nom: str
    telephone: str
    operateur: str
    pin: str

@router.post("/inscrire")
async def inscrire(demande: DemandeInscription):
    tel = demande.telephone.strip().replace(" ", "")

    # Verifier si deja existant
    if obtenir_client_par_telephone(tel):
        return {"succes": False, "erreur": "Ce numero est deja enregistre. Utilisez la connexion."}

    if len(demande.pin) != 4 or not demande.pin.isdigit():
        return {"succes": False, "erreur": "Le PIN doit contenir exactement 4 chiffres."}

    if len(demande.nom.strip()) < 2:
        return {"succes": False, "erreur": "Nom invalide."}

    nouveau = {
        "id": f"CUST-{demande.operateur.upper()[:4]}-{str(uuid.uuid4())[:8].upper()}",
        "operateur": demande.operateur,
        "telephone": tel,
        "nom": demande.nom.strip(),
        "pin": demande.pin,
        "statut_compte": "actif",
        "solde_xof": 0,
        "plafond_journalier_xof": 100000,
        "plafond_mensuel_xof": 300000,
        "total_transactions_30j": 0,
        "tentatives_pin_echouees": 0,
        "date_creation": datetime.now(timezone.utc).isoformat(),
        "derniere_activite": datetime.now(timezone.utc).isoformat(),
    }

    try:
        with open(CLIENTS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data["clients"].append(nouveau)
        else:
            data.append(nouveau)
        with open(CLIENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return {"succes": False, "erreur": f"Erreur sauvegarde : {e}"}

    return {"succes": True, "client": {"nom": nouveau["nom"], "telephone": tel, "operateur": demande.operateur}}
