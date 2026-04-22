"""
Routes rapports — generation et telechargement des rapports d'incidents.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, JSONResponse

from backend.services.rapport import generer_rapport_pdf, generer_rapport_json

router = APIRouter(prefix="/rapports", tags=["Rapports"])


@router.get("/{id_ticket}/pdf")
async def telecharger_rapport_pdf(id_ticket: str):
    """Genere et retourne le rapport PDF d'un ticket."""
    try:
        pdf_bytes = generer_rapport_pdf(id_ticket)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=rapport-{id_ticket}.pdf"},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur generation PDF : {e}")


@router.get("/{id_ticket}/json")
async def obtenir_rapport_json(id_ticket: str):
    """Retourne le rapport JSON structure d'un ticket."""
    try:
        return JSONResponse(content=generer_rapport_json(id_ticket))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))