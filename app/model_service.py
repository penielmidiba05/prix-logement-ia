"""Chargement du modèle entraîné et calcul des prédictions."""
import hashlib
import json
import logging
from pathlib import Path

import joblib
import pandas as pd

logger = logging.getLogger("api.modele")

class ServiceModele:
    """Garde en mémoire le pipeline scikit-learn et ses métadonnées."""

    def __init__(self, dossier: Path):
        self.dossier = Path(dossier)
        self.pipeline = None
        self.metadata: dict = {}
        self.sha256_charge: str | None = None

    def charger(self) -> None:
        chemin_modele = self.dossier / "model.joblib"
        chemin_meta = self.dossier / "metadata.json"
        if not chemin_modele.exists():
            raise FileNotFoundError(f"Modèle introuvable : {chemin_modele}")
        # On calcule l'empreinte du fichier réellement chargé, pour pouvoir la comparer.
        self.sha256_charge = hashlib.sha256(chemin_modele.read_bytes()).hexdigest()
        self.pipeline = joblib.load(chemin_modele)
        self.metadata = json.loads(chemin_meta.read_text(encoding="utf-8"))
        logger.info("Modèle %s chargé (sha256=%s...)",
                    self.metadata.get("version"), self.sha256_charge[:12])

    @property
    def pret(self) -> bool:
        return self.pipeline is not None

    def predire(self, caracteristiques: dict) -> float:
        # Le pipeline attend un tableau pandas avec les colonnes dans l'ordre de l'entraînement.
        ligne = pd.DataFrame([caracteristiques])[self.metadata["variables"]]
        ligne["bord_de_l_eau"] = ligne["bord_de_l_eau"].astype(int)
        return float(self.pipeline.predict(ligne)[0])