# Utiliser l'image Python officielle
FROM python:3.12-slim

# Les sorties (dont les mails du backend console) arrivent tout de suite dans les logs
ENV PYTHONUNBUFFERED=1

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances avant de copier le code : la couche reste en cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application dans le conteneur
COPY . .

# Exposer le port 8000
EXPOSE 8000

# Au démarrage (les settings ont besoin de l'environnement, absent au build) :
# migrations, statics, puis uvicorn. exec : uvicorn reçoit les signaux d'arrêt.
CMD ["sh", "-c", "python manage.py migrate --fake-initial && python manage.py collectstatic --noinput && exec uvicorn myportfolio.asgi:application --host 0.0.0.0 --port 8000"]
