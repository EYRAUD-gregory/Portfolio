"""Protection du formulaire de contact : vérification Turnstile et limites d'envoi."""
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'


def client_ip(request):
    # Derrière Cloudflare, l'adresse du visiteur arrive dans cet en-tête ; sinon (local),
    # c'est celle de la connexion. Un en-tête forgé ne contourne que la limite par adresse :
    # le plafond journalier, lui, ne dépend pas de l'adresse.
    return request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR', '')


def turnstile_enabled():
    return bool(settings.TURNSTILE_SITE_KEY and settings.TURNSTILE_SECRET_KEY)


def verify_turnstile(token, remote_ip):
    """Vrai si Cloudflare confirme le jeton. Tout doute (jeton absent, panne, réponse
    illisible) vaut refus."""
    if not turnstile_enabled():
        # Sans clés, seul le développement local (DEBUG) laisse passer
        if settings.DEBUG:
            return True
        logger.error("Turnstile n'est pas configuré : envoi refusé")
        return False
    if not token:
        return False

    # La requête est construite ici, champ par champ : rien d'autre du visiteur n'est relayé
    data = urllib.parse.urlencode({
        'secret': settings.TURNSTILE_SECRET_KEY,
        'response': token,
        'remoteip': remote_ip,
    }).encode()
    try:
        with urllib.request.urlopen(TURNSTILE_VERIFY_URL, data=data, timeout=5) as response:
            result = json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError):
        logger.exception("Vérification Turnstile impossible")
        return False
    return result.get('success') is True


def _count(key):
    return cache.get(key, 0)


def _increment(key, timeout):
    # add() ne crée la clé que si elle est absente : la durée court depuis le premier envoi
    cache.add(key, 0, timeout)
    cache.incr(key)


def _ip_key(remote_ip):
    return f'contact:ip:{remote_ip}'


def _day_key():
    return f'contact:day:{timezone.localdate().isoformat()}'


def ip_limit_reached(remote_ip):
    return _count(_ip_key(remote_ip)) >= settings.CONTACT_LIMIT_PER_IP_PER_HOUR


def daily_limit_reached():
    return _count(_day_key()) >= settings.CONTACT_LIMIT_PER_DAY


def record_attempt(remote_ip):
    """Tentative d'une adresse, comptée avant Turnstile (limite aussi les essais ratés)."""
    _increment(_ip_key(remote_ip), 60 * 60)


def record_send():
    """Mail réellement parti, compté après Turnstile : un robot refusé n'entame pas le
    plafond journalier et ne peut donc pas fermer le formulaire aux vrais visiteurs."""
    _increment(_day_key(), 24 * 60 * 60)
