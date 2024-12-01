from django.shortcuts import render
from django.core.mail import send_mail

from .forms import ContactForm
# Create your views here.
from .models import Profile, Formation, Project, ProjectIdea, Category


def portfolio_view(request):
    profile = Profile.objects.first()
    formations = Formation.objects.all().order_by('-starting_date')
    projects = Project.objects.all().order_by('-starting_date')
    project_ideas = ProjectIdea.objects.all()
    categories = Category.objects.prefetch_related('skills').all()

    confirmation_message = None  # Initialisation du message de confirmation

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            # Récupération des données
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]
            name = form.cleaned_data["name"]
            sender = form.cleaned_data["sender"]
            societe = form.cleaned_data.get("societe", "Non spécifié")  # Valeur par défaut
            telephone = form.cleaned_data.get("telephone", "Non spécifié")  # Valeur par défaut
            cc_myself = form.cleaned_data["cc_myself"]

            # Ajout des informations supplémentaires au message
            full_message = (
                f"Sujet : {subject}\n\n"
                f"Message : {message}\n\n"
                f"---\n"
                f"Société : {societe}\n"
                f"Téléphone : {telephone}\n"
                f"Envoyé par : {name} ({sender})\n"
            )

            # Destinataires
            recipients = ["gregory.eyraud@gmail.com"]
            if cc_myself:
                recipients.append(sender)

            # Envoi de l'email
            send_mail(subject, full_message, sender, recipients, fail_silently=False)

            confirmation_message = "Votre message a été envoyé avec succès !"
            form = ContactForm()
    else:
        form = ContactForm()

    return render(request, "portfolio/portfolio.html", {"form": form, "confirmation_message": confirmation_message,
                                                        'profile': profile,
                                                        'projects': projects,
                                                        'formations': formations,
                                                        'project_ideas': project_ideas,
                                                        'categories': categories})


def privacy_policy(request):
    return render(request, 'portfolio/politique_confidentialite.html')