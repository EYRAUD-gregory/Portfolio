import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render
from django.urls import reverse

from . import antispam
from .forms import ContactForm
from .models import Profile, Formation, Project, ProjectIdea, Category, Experience

logger = logging.getLogger(__name__)


def send_contact_email(cleaned_data):
    sender = cleaned_data["sender"]

    # Ajout des informations supplémentaires au message
    full_message = (
        f"Sujet : {cleaned_data['subject']}\n\n"
        f"Message : {cleaned_data['message']}\n\n"
        f"---\n"
        f"Société : {cleaned_data['societe'] or 'Non spécifié'}\n"
        f"Téléphone : {cleaned_data['telephone'] or 'Non spécifié'}\n"
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

    return render(request, "portfolio/portfolio.html", {
        'form': form,
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY if antispam.turnstile_enabled() else '',
        'profile': Profile.objects.first(),
        'projects': Project.objects.all().order_by('-starting_date'),
        'formations': Formation.objects.all().order_by('-starting_date'),
        'project_ideas': ProjectIdea.objects.all(),
        'experiences': Experience.objects.all().order_by('-starting_date'),
        'categories': Category.objects.prefetch_related('skills').all(),
    })


def privacy_policy(request):
    return render(request, 'portfolio/politique_confidentialite.html')


def mentions_legales(request):
    return render(request, 'portfolio/mentions_legales.html')
