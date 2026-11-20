"""Schémas Pydantic : la forme exacte des données échangées avec l'API."""
from pydantic import BaseModel, ConfigDict, Field, field_validator

class LogementEntree(BaseModel):
    """Caractéristiques d'un logement envoyées par le client (corps JSON de POST /predict)."""

    # extra="forbid" : un champ inconnu (faute de frappe, par exemple) provoque une erreur 422.
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{
            "surface_m2": 150, "chambres": 3, "salles_de_bain": 2, "etages": 1,
            "age_ans": 30, "distance_centre_km": 12, "bord_de_l_eau": False,
            "etat": 3, "qualite": 7,
        }]},
    )

    surface_m2: float = Field(..., ge=20, le=1300, description="Surface habitable en m²")
    chambres: int = Field(..., ge=1, le=10, description="Nombre de chambres")
    salles_de_bain: float = Field(..., ge=0.5, le=8,
                                  description="Salles de bain (0,5 = toilettes et lavabo seuls)")
    etages: float = Field(..., ge=1, le=3.5, description="Nombre de niveaux (1, 1,5, 2...)")
    age_ans: int = Field(..., ge=0, le=120, description="Âge du bâtiment au moment de la vente")
    distance_centre_km: float = Field(..., ge=0, le=80,
                                      description="Distance au centre-ville de Seattle, en km")
    bord_de_l_eau: bool = Field(..., description="Le terrain donne-t-il sur l'eau ?")
    etat: int = Field(..., ge=1, le=5, description="État général, de 1 (mauvais) à 5 (excellent)")
    qualite: int = Field(..., ge=1, le=13,
                         description="Note de construction du comté de King, de 1 à 13")

    @field_validator("salles_de_bain")
    @classmethod
    def multiple_de_un_quart(cls, valeur: float) -> float:
        # Dans le jeu de données, les salles de bain se comptent par quarts (0,25 ; 0,5 ; 0,75...).
        if round(valeur * 4) != valeur * 4:
            raise ValueError("doit être un multiple de 0,25 (ex. 1, 1.5, 2.25)")
        return valeur

    @field_validator("etages")
    @classmethod
    def multiple_de_un_demi(cls, valeur: float) -> float:
        if round(valeur * 2) != valeur * 2:
            raise ValueError("doit être un multiple de 0,5 (ex. 1, 1.5, 2)")
        return valeur

class PredictionSortie(BaseModel):
    """Réponse renvoyée par POST /predict."""
    prix_estime_usd: float = Field(..., description="Prix estimé, en dollars américains")
    devise: str = "USD"
    version_modele: str
    duree_ms: float = Field(..., description="Temps de calcul de la prédiction côté serveur")

class SanteSortie(BaseModel):
    """Réponse de GET /health."""
    statut: str
    modele_charge: bool