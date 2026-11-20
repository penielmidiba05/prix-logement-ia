"""
Exploration rapide du jeu de données, AVANT l'entraînement.
"""
import pandas as pd

df = pd.read_csv("data/kc_house_data.csv")

print("Dimensions (lignes, colonnes) :", df.shape)
print("\nColonnes et types :")
print(df.dtypes.to_string())

print("\nValeurs manquantes au total :", int(df.isna().sum().sum()))
print("Identifiants en double (maisons revendues) :", int(df["id"].duplicated().sum()))
print("Période des ventes :", df["date"].min()[:8], "->", df["date"].max()[:8])

print("\nStatistiques des colonnes utiles :")
colonnes = ["price", "sqft_living", "bedrooms", "bathrooms", "floors", "yr_built",
            "condition", "grade", "waterfront"]
print(df[colonnes].describe().round(1).T.to_string())

print("\nRépartition du nombre de chambres (repérez les valeurs suspectes) :")
print(df["bedrooms"].value_counts().sort_index().to_string())
print("\nLogements avec 0 salle de bain :", int((df["bathrooms"] == 0).sum()))