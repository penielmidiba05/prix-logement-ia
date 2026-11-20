# Image de l'API de prédiction du prix d'un logement

#  1. Image de base officielle : Debian minimale + Python 3.13
FROM python:3.13-slim

# 2. Réglages Python : pas de fichiers .pyc, journaux affichés immédiatement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 3. Dossier de travail dans le conteneur
WORKDIR /app

# 4. Dépendances d'abord : cette couche reste en cache tant que requirements.txt ne change pas
COPY requirements.txt .
RUN pip install -r requirements.txt

# 5. Code de l'application et modèle entraîné
COPY app/ ./app/
COPY model/ ./model/

# 6. Sécurité : on n'exécute pas le serveur en tant que root
RUN useradd --create-home --uid 10001 appuser
USER appuser

# 7. Port d'écoute documenté (le mapping réel se fait avec docker run -p)
EXPOSE 8000

# 8. Sonde de santé utilisée par Docker en local (les services Cloud ont leurs propres sondes)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

# 9. Commande de démarrage : 0.0.0.0 pour accepter les connexions venant de l'extérieur du conteneur
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]