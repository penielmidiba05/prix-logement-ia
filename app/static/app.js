// Interface Web : lit le formulaire, appelle POST /predict et affiche la réponse réelle de l'API.
const formulaire = document.getElementById("formulaire");
const bouton = document.getElementById("bouton");
const zoneResultat = document.getElementById("resultat");
const zoneErreur = document.getElementById("erreur");
const formatUSD = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

// Libellés lisibles pour les messages d'erreur renvoyés par l'API (codes 422).
const LIBELLES = {
  surface_m2: "Surface", chambres: "Chambres", salles_de_bain: "Salles de bain",
  etages: "Niveaux", age_ans: "Âge", distance_centre_km: "Distance",
  bord_de_l_eau: "Bord de l'eau", etat: "État", qualite: "Qualité",
};

// 1. Au chargement : on interroge /model-info pour afficher la version réellement déployée.
fetch("/model-info")
  .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
  .then((m) => {
    document.getElementById("info-modele").textContent =
      `Modèle ${m.version} · entraîné le ${m.entraine_le} · erreur moyenne (MAE) sur le jeu de test : ` +
      `${formatUSD.format(m.metriques_test.MAE_usd)} · intégrité : ${m.integrite_ok ? "vérifiée" : "NON vérifiée"}`;
  })
  .catch(() => {
    document.getElementById("info-modele").textContent = "API injoignable : vérifiez que le serveur est démarré.";
  });

function afficherErreur(texte) {
  zoneResultat.hidden = true;
  zoneErreur.textContent = texte;
  zoneErreur.hidden = false;
}

// 2. Validation côté navigateur : retour immédiat à l'utilisateur, avant tout appel réseau.
function lireFormulaire() {
  const champs = formulaire.querySelectorAll("input[type=number]");
  const problemes = [];
  champs.forEach((c) => {
    c.classList.add("touche");
    if (!c.checkValidity()) problemes.push(`${LIBELLES[c.name]} : ${c.validationMessage}`);
  });
  if (problemes.length) return { erreurs: problemes };
  const d = new FormData(formulaire);
  return {
    donnees: {
      surface_m2: Number(d.get("surface_m2")),
      chambres: Number(d.get("chambres")),
      salles_de_bain: Number(d.get("salles_de_bain")),
      etages: Number(d.get("etages")),
      age_ans: Number(d.get("age_ans")),
      distance_centre_km: Number(d.get("distance_centre_km")),
      bord_de_l_eau: d.get("bord_de_l_eau") === "on",
      etat: Number(d.get("etat")),
      qualite: Number(d.get("qualite")),
    },
    cle: d.get("cle_api"),
  };
}

// 3. Envoi à l'API et affichage du résultat ou de l'erreur.
formulaire.addEventListener("submit", async (evenement) => {
  evenement.preventDefault();
  zoneErreur.hidden = true;
  const lecture = lireFormulaire();
  if (lecture.erreurs) return afficherErreur("Corrigez les champs suivants :\n" + lecture.erreurs.join("\n"));

  const entetes = { "Content-Type": "application/json" };
  if (lecture.cle) entetes["X-API-Key"] = lecture.cle;

  bouton.disabled = true;
  try {
    const reponse = await fetch("/predict", { method: "POST", headers: entetes, body: JSON.stringify(lecture.donnees) });
    const corps = await reponse.json();
    if (reponse.status === 422) {
      // FastAPI renvoie une liste d'erreurs : [{loc: ["body", "champ"], msg: "..."}]
      const lignes = corps.detail.map((e) => `${LIBELLES[e.loc[e.loc.length - 1]] || e.loc.join(".")} : ${e.msg}`);
      return afficherErreur("L'API a refusé les données :\n" + lignes.join("\n"));
    }
    if (!reponse.ok) return afficherErreur(`Erreur ${reponse.status} : ${corps.detail}`);

    document.getElementById("prix").textContent = formatUSD.format(corps.prix_estime_usd);
    document.getElementById("detail").textContent =
      `Modèle ${corps.version_modele} · calcul en ${corps.duree_ms} ms`;
    zoneResultat.hidden = false;
  } catch (e) {
    afficherErreur("Impossible de joindre l'API : " + e.message);
  } finally {
    bouton.disabled = false;
  }
});