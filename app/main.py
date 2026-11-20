"""
API FastAPI de prédiction du prix d'un logement.

Lancement local (depuis la racine du projet) :
    uvicorn app.main:app --reload --port 8000
Documentation interactive : http://127.0.0.1:8000/docs
"""
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles

from app.model_service import ServiceModele
from app.schemas import LogementEntree, PredictionSortie, SanteSortie

# ------------------------------------------------------------------
# Configuration par variables d'environnement (même image partout)
# ------------------------------------------------------------------
RACINE = Path(__file__).resolve().parent.parent
DOSSIER_MODELE = Path(os.getenv("MODEL_DIR", RACINE / "model"))
CLE_API = os.getenv("API_KEY")          # facultative : si vide, /predict reste ouvert
NIVEAU_LOG = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(level=NIVEAU_LOG,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("api")

service = ServiceModele(DOSSIER_MODELE)

@asynccontextmanager
async def cycle_de_vie(app: FastAPI):
    # Exécuté UNE fois au démarrage du serveur, avant la première requête.
    try:
        service.charger()
    except Exception:
        logger.exception("Échec du chargement du modèle : l'API démarre en mode dégradé")
    yield
    # Code exécuté à l'arrêt du serveur (rien à libérer ici).

app = FastAPI(
    title="API de prédiction du prix d'un logement",
    description="Modèle scikit-learn entraîné sur les ventes du comté de King (Seattle, 2014-2015).",
    version="1.0.0",
    lifespan=cycle_de_vie,
)

lecteur_cle = APIKeyHeader(name="X-API-Key", auto_error=False)

def verifier_cle(cle: str | None = Security(lecteur_cle)) -> None:
    """Si une clé est configurée sur le serveur, le client doit l'envoyer dans X-API-Key."""
    if CLE_API and cle != CLE_API:
        raise HTTPException(status_code=401, detail="Clé d'API absente ou invalide")

@app.get("/health", response_model=SanteSortie, tags=["supervision"])
def sante():
    """Sonde de santé : 200 si le modèle est chargé, 503 sinon."""
    if not service.pret:
        return JSONResponse(status_code=503,
                            content={"statut": "indisponible", "modele_charge": False})
    return SanteSortie(statut="ok", modele_charge=True)

@app.get("/model-info", tags=["supervision"])
def informations_modele():
    """Métadonnées du modèle déployé et contrôle de son intégrité."""
    if not service.pret:
        raise HTTPException(status_code=503, detail="Modèle non chargé")
    attendu = service.metadata.get("sha256_modele")
    return {
        **service.metadata,
        "sha256_fichier_charge": service.sha256_charge,
        "integrite_ok": attendu == service.sha256_charge,
    }

@app.post("/predict", response_model=PredictionSortie, tags=["prédiction"],
          dependencies=[Depends(verifier_cle)])
def predire(logement: LogementEntree):
    """Renvoie le prix estimé d'un logement à partir de ses 9 caractéristiques."""
    if not service.pret:
        raise HTTPException(status_code=503, detail="Modèle non chargé")
    debut = time.perf_counter()
    prix = service.predire(logement.model_dump())
    duree = (time.perf_counter() - debut) * 1000
    logger.info("prediction entree=%s prix=%.0f duree_ms=%.1f",
                logement.model_dump_json(), prix, duree)
    return PredictionSortie(prix_estime_usd=round(prix, 2),
                            version_modele=service.metadata["version"],
                            duree_ms=round(duree, 2))

@app.exception_handler(Exception)
async def erreur_inattendue(request: Request, exc: Exception):
    # Toute erreur non prévue : on la journalise et on ne divulgue pas de détails au client.
    logger.exception("Erreur inattendue sur %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur"})

# Interface Web : fichiers statiques servis par la même application

DOSSIER_STATIC = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=DOSSIER_STATIC), name="static")

@app.get("/", include_in_schema=False)
def accueil():
    return FileResponse(DOSSIER_STATIC / "index.html")