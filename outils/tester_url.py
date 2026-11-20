"""
Teste une API déployée (locale ou Cloud) avec plusieurs logements, valides et invalides.
N'utilise que la bibliothèque standard de Python : aucune installation nécessaire.

Utilisation :
    python outils/tester_url.py http://127.0.0.1:8000
    python outils/tester_url.py https://<votre-url-cloud>
"""
import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"
TYPE = {"surface_m2": 150, "chambres": 3, "salles_de_bain": 2, "etages": 1, "age_ans": 30,
        "distance_centre_km": 12, "bord_de_l_eau": False, "etat": 3, "qualite": 7}

CAS = [
    ("Maison type", TYPE, 200),
    ("Petit appartement ancien", {**TYPE, "surface_m2": 60, "chambres": 1, "salles_de_bain": 1,
                                  "age_ans": 80, "distance_centre_km": 3}, 200),
    ("Grande maison récente au bord de l'eau", {**TYPE, "surface_m2": 320, "chambres": 5,
                                                "salles_de_bain": 3.5, "etages": 2, "age_ans": 5,
                                                "bord_de_l_eau": True, "qualite": 10}, 200),
    ("Surface négative", {**TYPE, "surface_m2": -5}, 422),
    ("État hors bornes", {**TYPE, "etat": 9}, 422),
    ("Champ manquant", {k: v for k, v in TYPE.items() if k != "qualite"}, 422),
]

def appeler(methode, chemin, corps=None):
    donnees = json.dumps(corps).encode() if corps is not None else None
    requete = urllib.request.Request(BASE + chemin, data=donnees, method=methode,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(requete, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")

statut, sante = appeler("GET", "/health")
print(f"GET /health      -> {statut} {sante}")
statut, info = appeler("GET", "/model-info")
print(f"GET /model-info  -> {statut} version={info.get('version')} sha256={str(info.get('sha256_fichier_charge'))[:16]}...")

reussis = 0
for nom, corps, attendu in CAS:
    statut, rep = appeler("POST", "/predict", corps)
    ok = statut == attendu
    reussis += ok
    detail = f"{rep['prix_estime_usd']:,.0f} USD" if statut == 200 else rep.get("detail", [{}])[0].get("msg", rep)
    print(f"[{'OK ' if ok else 'ÉCHEC'}] {nom:42s} -> {statut} (attendu {attendu}) {detail}")
print(f"\n{reussis}/{len(CAS)} cas conformes")