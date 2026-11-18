"""Alerte ntfy à chaque envoi du formulaire, réussi ou non : aucun message n'est gardé en base,
c'est le seul signal d'un échec silencieux. L'alerte ne transporte rien du visiteur."""
import http.client
import logging
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

SENT = {
    'title': 'Portfolio : nouveau message',
    'message': 'Le formulaire de contact a envoyé un mail vers ta boîte.',
    'priority': 'default',
}
FAILED = {
    'title': "Portfolio : échec d'envoi",
    'message': "Un envoi du formulaire de contact a échoué. Le détail est dans les journaux du site.",
    'priority': 'high',
}


def _publish(alert):
    # L'adresse contient le sujet ntfy, qui fait office de secret : elle n'est jamais journalisée
    url = settings.CONTACT_NTFY_URL
    if not url:
        return
    # Titre et priorité en paramètres d'adresse : les en-têtes HTTP n'acceptent pas les accents
    query = urllib.parse.urlencode({'title': alert['title'], 'priority': alert['priority']})
    request = urllib.request.Request(
        f'{url}?{query}', data=alert['message'].encode(), method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=5):
            pass
    except (OSError, http.client.HTTPException, ValueError) as error:
        # OSError couvre URLError, HTTPError, délai dépassé et connexion coupée
        # Une alerte perdue ne doit pas faire échouer le formulaire
        logger.warning("Alerte ntfy impossible (%s)", type(error).__name__)


def contact_sent():
    _publish(SENT)


def contact_failed():
    _publish(FAILED)
