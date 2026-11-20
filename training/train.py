"""
Entraînement du modèle de prédiction du prix d'un logement.

Données : « House Sales in King County, USA » (ventes de maisons du comté de
King, État de Washington, entre mai 2014 et mai 2015), licence CC0.
Source : https://www.kaggle.com/datasets/harlfoxem/housesalesprediction

Résultat : model/model.joblib et model/metadata.json
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# 1. Constantes du projet
VERSION_MODELE = "1.0.0"
GRAINE = 42                      # graine aléatoire : résultats reproductibles
PIED2_VERS_M2 = 0.09290304       # 1 pied carré = 0,09290304 m²
CENTRE_SEATTLE = (47.6062, -122.3321)  # point de référence du centre-ville

# Les 9 variables que l'API recevra, dans cet ordre.
VARIABLES = [
    "surface_m2", "chambres", "salles_de_bain", "etages", "age_ans",
    "distance_centre_km", "bord_de_l_eau", "etat", "qualite",
]
CIBLE = "prix"

def distance_km(lat, lon, lat0, lon0):
    """Distance à vol d'oiseau (formule de haversine), en kilomètres."""
    rayon_terre = 6371.0
    phi1, phi2 = np.radians(lat), np.radians(lat0)
    dphi = np.radians(lat0 - lat)
    dlmb = np.radians(lon0 - lon)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlmb / 2) ** 2
    return 2 * rayon_terre * np.arcsin(np.sqrt(a))

def charger_et_preparer(chemin_csv: Path) -> pd.DataFrame:
    """Lit le CSV brut, le nettoie et calcule les 9 variables du modèle."""
    brut = pd.read_csv(chemin_csv)
    print(f"[1] Lecture : {len(brut)} lignes, {brut.shape[1]} colonnes")

    attendues = {"id", "date", "price", "bedrooms", "bathrooms", "sqft_living",
                 "floors", "waterfront", "condition", "grade", "yr_built", "lat", "long"}
    manquantes = attendues - set(brut.columns)
    if manquantes:
        raise ValueError(f"Colonnes absentes du fichier : {sorted(manquantes)}")

    # Une même maison peut avoir été vendue deux fois : on garde la vente la plus récente.
    df = brut.sort_values("date").drop_duplicates(subset="id", keep="last").copy()
    print(f"[2] Après suppression des reventes : {len(df)} lignes")

    # Nettoyage : valeurs impossibles ou aberrantes (ex. 33 chambres, 0 salle de bain).
    df = df[(df["bedrooms"].between(1, 10)) & (df["bathrooms"] > 0) & (df["price"] > 0)]
    print(f"[3] Après nettoyage : {len(df)} lignes")

    # Variables dérivées, toutes calculées à partir de colonnes réelles.
    annee_vente = df["date"].str[:4].astype(int)
    prepare = pd.DataFrame({
        "surface_m2": (df["sqft_living"] * PIED2_VERS_M2).round(1),
        "chambres": df["bedrooms"].astype(int),
        "salles_de_bain": df["bathrooms"].astype(float),
        "etages": df["floors"].astype(float),
        "age_ans": (annee_vente - df["yr_built"]).clip(lower=0).astype(int),
        "distance_centre_km": distance_km(df["lat"], df["long"], *CENTRE_SEATTLE).round(2),
        "bord_de_l_eau": df["waterfront"].astype(int),
        "etat": df["condition"].astype(int),
        "qualite": df["grade"].astype(int),
        CIBLE: df["price"].astype(float),
    })
    return prepare

def construire_pipeline(regresseur) -> TransformedTargetRegressor:
    """ préparation des colonnes + modèle + transformation de la cible."""
    preparation = ColumnTransformer(
        transformers=[("num", Pipeline([
            ("imputation", SimpleImputer(strategy="median")),
            ("normalisation", StandardScaler()),
        ]), VARIABLES)],
        remainder="drop",
    )
    pipeline = Pipeline([("preparation", preparation), ("modele", regresseur)])
    # Les prix sont très asymétriques : on apprend log(1 + prix), puis on revient en dollars.
    return TransformedTargetRegressor(regressor=pipeline, func=np.log1p, inverse_func=np.expm1)

def evaluer(modele, X_test, y_test) -> dict:
    prediction = modele.predict(X_test)
    return {
        "MAE_usd": round(float(mean_absolute_error(y_test, prediction)), 0),
        "RMSE_usd": round(float(root_mean_squared_error(y_test, prediction)), 0),
        "R2": round(float(r2_score(y_test, prediction)), 4),
    }

def main():
    parser = argparse.ArgumentParser(description="Entraîne le modèle de prix des logements.")
    parser.add_argument("--data", default="data/kc_house_data.csv")
    parser.add_argument("--out", default="model")
    args = parser.parse_args()

    donnees = charger_et_preparer(Path(args.data))
    X, y = donnees[VARIABLES], donnees[CIBLE]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=GRAINE)
    print(f"[4] Découpage : {len(X_train)} pour l'entraînement, {len(X_test)} pour le test")

    # Modèle de référence (simple) puis modèle principal.
    reference = construire_pipeline(LinearRegression()).fit(X_train, y_train)
    principal = construire_pipeline(
        HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06, random_state=GRAINE)
    ).fit(X_train, y_train)

    scores_ref = evaluer(reference, X_test, y_test)
    scores = evaluer(principal, X_test, y_test)
    print(f"[5] Régression linéaire       : {scores_ref}")
    print(f"[5] Gradient boosting (choisi): {scores}")

    # Sauvegarde du pipeline complet (préparation + modèle + transformation de la cible).
    dossier = Path(args.out)
    dossier.mkdir(parents=True, exist_ok=True)
    chemin_modele = dossier / "model.joblib"
    joblib.dump(principal, chemin_modele, compress=3)
    empreinte = hashlib.sha256(chemin_modele.read_bytes()).hexdigest()

    metadata = {
        "nom": "prix-logement-king-county",
        "version": VERSION_MODELE,
        "entraine_le": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "algorithme": "HistGradientBoostingRegressor (cible log1p)",
        "scikit_learn": sklearn.__version__,
        "variables": VARIABLES,
        "plages_observees": {c: [float(X[c].min()), float(X[c].max())] for c in VARIABLES},
        "metriques_test": scores,
        "metriques_reference_lineaire": scores_ref,
        "lignes_entrainement": int(len(X_train)),
        "lignes_test": int(len(X_test)),
        "jeu_de_donnees": "House Sales in King County, USA (mai 2014 - mai 2015), licence CC0",
        "source": "https://www.kaggle.com/datasets/harlfoxem/housesalesprediction",
        "point_reference_centre": {"lat": CENTRE_SEATTLE[0], "lon": CENTRE_SEATTLE[1]},
        "devise": "USD",
        "sha256_modele": empreinte,
    }
    (dossier / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False),
                                           encoding="utf-8")
    print(f"[6] Modèle enregistré : {chemin_modele} ({chemin_modele.stat().st_size // 1024} Ko)")
    print(f"    Empreinte SHA-256 : {empreinte}")

    # Test d'une prédiction sur une maison inventée pour l'exemple (pas une ligne du jeu).
    exemple = pd.DataFrame([{
        "surface_m2": 150.0, "chambres": 3, "salles_de_bain": 2.0, "etages": 1.0, "age_ans": 30,
        "distance_centre_km": 12.0, "bord_de_l_eau": 0, "etat": 3, "qualite": 7,
    }])
    prix = principal.predict(exemple)[0]
    print(f"[7] Exemple : maison de 150 m², 3 chambres, à 12 km -> {prix:,.0f} USD")

if __name__ == "__main__":
    main()