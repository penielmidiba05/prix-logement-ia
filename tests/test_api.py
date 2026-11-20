"""Tests automatiques de l'API. Lancement : python -m pytest -v"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

LOGEMENT = {
    "surface_m2": 150, "chambres": 3, "salles_de_bain": 2, "etages": 1, "age_ans": 30,
    "distance_centre_km": 12, "bord_de_l_eau": False, "etat": 3, "qualite": 7,
}

@pytest.fixture(scope="module")
def client():
    # Le bloc « with » déclenche le démarrage de l'application, donc le chargement du modèle.
    with TestClient(app) as c:
        yield c

def test_sante(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"statut": "ok", "modele_charge": True}

def test_informations_modele(client):
    r = client.get("/model-info")
    assert r.status_code == 200
    corps = r.json()
    assert corps["integrite_ok"] is True
    assert len(corps["variables"]) == 9

def test_prediction_valide(client):
    r = client.post("/predict", json=LOGEMENT)
    assert r.status_code == 200
    prix = r.json()["prix_estime_usd"]
    assert 50_000 < prix < 5_000_000      # ordre de grandeur plausible pour ce marché

def test_plus_grand_est_plus_cher(client):
    petit = client.post("/predict", json={**LOGEMENT, "surface_m2": 80}).json()["prix_estime_usd"]
    grand = client.post("/predict", json={**LOGEMENT, "surface_m2": 300}).json()["prix_estime_usd"]
    assert grand > petit

@pytest.mark.parametrize("champ, valeur", [
    ("surface_m2", -5), ("chambres", 0), ("etat", 9), ("salles_de_bain", 1.3), ("etages", 1.2),
])
def test_valeurs_refusees(client, champ, valeur):
    r = client.post("/predict", json={**LOGEMENT, champ: valeur})
    assert r.status_code == 422

def test_champ_manquant(client):
    incomplet = {k: v for k, v in LOGEMENT.items() if k != "qualite"}
    assert client.post("/predict", json=incomplet).status_code == 422

def test_champ_inconnu(client):
    assert client.post("/predict", json={**LOGEMENT, "piscine": True}).status_code == 422

def test_interface_web(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Estimation du prix" in r.text