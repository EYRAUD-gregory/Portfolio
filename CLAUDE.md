# CLAUDE.md — Portfolio

Site portfolio Django (une app `portfolio`, contenu saisi via l'admin) + formulaire de contact.
Un chatbot public viendra plus tard (jalon 3) : **hors périmètre tant que le jalon 1 n'est pas fini.**

Les décisions et leur motif vivent dans les notes du projet, hors repo (`PORTFOLIO.md`, monté avec
`--add-dir` quand il est fourni). Ce fichier ne contient que les règles du repo. **Ce repo est public :
rien de ce qui est écrit ici, ni dans un commit, ne doit révéler un secret ou un détail d'infra.**

## Cible technique

- Django **5.2 LTS** (`>=5.2,<5.3`), Python **3.12**.
- **ASGI / uvicorn** (`myportfolio.asgi:application`). Pas de worker gunicorn sync : le futur endpoint
  SSE bloquerait un worker par visiteur.
- Postgres, WhiteNoise pour les statics, **médias en `MEDIA_ROOT` local** (Cloudinary retiré).
- Toute la config qui varie entre local et prod passe par variables d'environnement.

## Jalon 1 — « déployable en local » : ordre imposé

1. **Garde-fous d'abord** : hook pre-commit gitleaks ; `.gitignore` corrigé (`*.sql` au lieu de `.sql`,
   `sauvegardes/`, `media/`, `.env` ; **retirer `migrations/`**). Rien d'autre avant ça.
2. **Dépendances** : Django 5.2, retrait de `cloudinary`, `django-cloudinary-storage` et de ce qui
   n'est pas importé (`python-decouple`) ; versions épinglées. Dockerfile en `python:3.12-slim`.
3. **`settings.py`** : dict `STORAGES` (remplace `STATICFILES_STORAGE`/`DEFAULT_FILE_STORAGE`, supprimés
   en 5.1) ; `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SECURE_SSL_REDIRECT` lus
   depuis l'env ; `SESSION_COOKIE_SECURE` ; WhiteNoise **juste après** `SecurityMiddleware`.
   Ajouter un `.env.example` avec des valeurs factices.
4. **Migrations** : générer depuis les models actuels et les committer (jamais versionnées jusqu'ici).
5. **ASGI** : lancement uvicorn, Dockerfile et compose alignés.
6. **Formulaire de contact** (voir invariants) : `EmailMessage`, expéditeur transactionnel configuré par
   l'env, `cc_myself` supprimé du form, de la vue et du template.
7. **Compose local** : image `postgres:18` épinglée, volume Postgres **monté** sur `/var/lib/postgresql`
   (pas `/data` : depuis la 18, l'image range ses données dans `18/docker` et refuse ce point de montage), volume médias monté,
   `env_file`, `collectstatic` au démarrage du conteneur (pas au build). Aucun `ports:` sur `db`.
8. **Purge** : `main.py` (gabarit PyCharm), `static/admin/` committé (régénéré par `collectstatic`).

Une étape = un commit. Ne pas enchaîner l'étape suivante si la vérification de la précédente échoue.

## Invariants — ne jamais enfreindre

- **Aucun secret dans le repo**, même temporairement, même dans un test. L'historique a déjà fui une fois.
- **Ne pas lire `.env`, `*.sql` ni `sauvegardes/`**, ni par un détour (`docker compose config`, `env`,
  script qui affiche l'environnement). Si une valeur est nécessaire, demander.
- Le `.env` local ne contient **que des valeurs de dev** : pendant le jalon 1, `EMAIL_BACKEND` console,
  aucune vraie clé d'expéditeur. Les secrets réels n'existent que sur la machine de prod.
- **Une adresse saisie par un visiteur n'est jamais un destinataire.** Elle va dans `reply_to`, point.
  `from_email` = le compte SMTP configuré ; destinataire = constante issue de l'env. Arguments **nommés**
  sur tout appel d'envoi (`sender` humain ≠ `from_email` SMTP : ce télescopage a déjà produit un relais ouvert).
- **Modale projet** (`portfolio.html` → `script.js`) : la chaîne `escapejs` → `JSON.parse` → `innerHTML`
  annule l'échappement. Ne **pas** retirer `escapejs` seul (casse `JSON.parse` au premier guillemet).
  Le correctif touche les deux côtés en une passe : affichage en `textContent`, retours à la ligne en CSS.
- **Postgres ne publie jamais de port.** Docker contourne le pare-feu de l'hôte ; seul le service web
  l'atteint, par le réseau interne du compose.
- **`/admin/`** sera restreint au réseau privé au niveau du reverse proxy : ne pas y ajouter de vue
  publique, ne pas créer d'autre route d'administration.
- Les données (base + médias) n'existent qu'en un exemplaire : **aucune commande destructive** sur un
  volume ou un dump (`down -v`, `flush`, `DROP`) sans confirmation explicite.

## Pièges connus

- Le dump existant porte sa propre table `django_migrations`, produite par des migrations jamais
  versionnées. Le restaurer sur des migrations fraîches peut faire rejouer des `CREATE TABLE` :
  tester sur une base jetable, jamais sur la seule copie.
- `collectstatic` exige que les settings chargent : sans `SECRET_KEY`, il échoue (le `.env` est exclu
  du contexte Docker).
- `CSRF_TRUSTED_ORIGINS` : schéma + hôte, **sans slash final**, sinon la comparaison échoue.
- Le `--timeout` gunicorn (30 s) tue le worker, pas seulement la requête : à retenir pour le SSE.

## Hors périmètre

VPS, DNS, reverse proxy, réseau privé, backend LLM : se font ailleurs. Aucune commande sur un serveur distant.

## Avant de dire « fini »

- `python manage.py check --deploy` avec un env de prod factice : zéro warning non justifié.
- `python manage.py makemigrations --check --dry-run` : rien à générer.
- `docker compose up` depuis zéro → page d'accueil en 200, admin accessible ;
  `docker compose down` puis `up` → **le contenu est toujours là**.
- Formulaire testé avec `EMAIL_BACKEND` console : un seul destinataire, visiteur en `Reply-To`.
- `gitleaks detect` propre sur l'arbre de travail.