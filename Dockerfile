# Utiliser l'image Python officielle
FROM python:3.10-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

RUN python manage.py collectstatic --noinput

# Copier tout le code de l'application dans le conteneur
COPY . .

# Exposer le port 8000
EXPOSE 8000

# Commande pour démarrer le serveur Django
CMD ["gunicorn", "--bind", "localhost:8000", "myportfolio.wsgi:application"]