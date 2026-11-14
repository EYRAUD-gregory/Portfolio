import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.db.models import F, Prefetch
from django.shortcuts import redirect, render
from django.urls import reverse

from . import antispam
from .forms import ContactForm
from .graph import build_details, build_graph, initials
from .models import Profile, Formation, Project, Category, Experience, Skill

logger = logging.getLogger(__name__)

# Du plus récent au plus ancien ; un élément sans date va à la fin
# (par défaut, Postgres place les valeurs vides en tête d'un tri décroissant)
NEWEST_FIRST = F('starting_date').desc(nulls_last=True)


def send_contact_email(cleaned_data):
    sender = cleaned_data["sender"]

    # Ajout des informations supplémentaires au message
    full_message = (
        f"Sujet : {cleaned_data['subject']}\n\n"
        f"Message : {cleaned_data['message']}\n\n"
        f"---\n"
        f"Envoyé par : {cleaned_data['name']} ({sender})\n"
    )

    # L'adresse du visiteur ne sert qu'à répondre (reply_to),
    # jamais de destinataire ni d'expéditeur (sinon : relais ouvert)
    EmailMessage(
        subject=cleaned_data["subject"],
        body=full_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.CONTACT_RECIPIENT],
        reply_to=[sender],
    ).send(fail_silently=False)


def portfolio_view(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            remote_ip = antispam.client_ip(request)
            if antispam.ip_limit_reached(remote_ip) or antispam.daily_limit_reached():
                form.add_error(None, "Trop de messages ont été envoyés. Merci de réessayer plus tard.")
            else:
                antispam.record_attempt(remote_ip)
                if not antispam.verify_turnstile(request.POST.get('cf-turnstile-response', ''), remote_ip):
                    form.add_error(None, "La vérification anti-robot a échoué. Merci de réessayer.")
                else:
                    try:
                        send_contact_email(form.cleaned_data)
                    except Exception:
                        # Journalisé sans le contenu du message ; le formulaire reste rempli
                        logger.exception("Échec de l'envoi du formulaire de contact")
                        form.add_error(None, "Votre message n'a pas pu être envoyé. Merci de réessayer plus tard.")
                    else:
                        antispam.record_send()
                        # Redirection après POST : recharger la page ne renvoie pas le message,
                        # et l'ancre ramène le visiteur sur la confirmation
                        messages.success(request, "Votre message a été envoyé avec succès !")
                        return redirect(reverse('portfolio_view') + '#contact')
    else:
        form = ContactForm()

    profile = Profile.objects.first()
    # Les technos sont chargées en une requête par liste, dans un ordre stable :
    # la disposition du graphe en dépend
    skills = Prefetch('skills', queryset=Skill.objects.order_by('name'))
    experiences = list(Experience.objects.prefetch_related(skills).order_by(NEWEST_FIRST))
    # Les projets mis en avant passent en tête : ce sont les cartes larges
    projects = list(Project.objects.prefetch_related(skills).order_by('-featured', NEWEST_FIRST))
    items = experiences + projects
    graph = build_graph(profile, items)

    return render(request, "portfolio/portfolio.html", {
        'form': form,
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY if antispam.turnstile_enabled() else '',
        'profile': profile,
        'initials': initials(profile.name) if profile else '',
        'taglines': profile.tagline_list() if profile else [],
        # Cartes : les projets commencés, terminés ou en cours. Les idées ont leur propre bloc.
        'projects': [p for p in projects if not p.is_idea],
        'project_ideas': [p for p in projects if p.is_idea],
        'formations': Formation.objects.all().order_by(NEWEST_FIRST),
        'experiences': experiences,
        'categories': Category.objects.prefetch_related('skills').all(),
        # Graphe du bandeau et fenêtre de détail : des valeurs, que le script écrit en texte
        'graph': graph,
        # Sans rien à relier, le bandeau se passe du graphe
        'has_graph': len(graph['nodes']) > 1,
        'graph_has_techs': any(node['type'] == 'tech' for node in graph['nodes']),
        'details': build_details(items),
    })


def legal_context():
    # La barre et le pied de page des pages légales affichent le nom du profil
    profile = Profile.objects.first()
    return {'profile': profile, 'initials': initials(profile.name) if profile else ''}


def privacy_policy(request):
    return render(request, 'portfolio/politique_confidentialite.html', legal_context())


def mentions_legales(request):
    return render(request, 'portfolio/mentions_legales.html', legal_context())
