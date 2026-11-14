import re

from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.formats import date_format

# Liens saisis en HTML dans d'anciennes descriptions : leurs balises n'ont pas leur place sur une carte
LINK_TAG = re.compile(r'<a\s[^>]*>|</a>')


def period_label(start, end):
    """« septembre 2023 – juin 2024 » ; un seul mois si les deux dates tombent le même, rien sans date."""
    months = dict.fromkeys(date_format(day, 'F Y') for day in (start, end) if day)
    return ' – '.join(months)


def first_sentence(text, limit=200):
    """Résumé de secours d'une carte, tant que le champ « résumé » n'est pas rempli."""
    text = ' '.join(LINK_TAG.sub('', text).split())
    sentence = re.split(r'(?<=[.!?])\s', text, maxsplit=1)[0]
    if len(sentence) <= limit:
        return sentence
    # Trop longue : coupée sur un mot entier
    return sentence[:limit - 1].rsplit(' ', 1)[0] + '…'


class Profile(models.Model):
    name = models.CharField(max_length=100)
    bio = models.TextField()
    contact_email = models.EmailField()
    linkedin = models.URLField(blank=True)
    github = models.URLField(blank=True)
    image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    # Textes qui défilent sous le nom, dans le bandeau d'accueil
    taglines = models.TextField("accroches du bandeau", blank=True, help_text="Une accroche par ligne.")
    # Phrase fixe sous les accroches : qui je suis et ce que je fais, en une ligne
    lead = models.CharField(
        "phrase de présentation", max_length=300, blank=True,
        help_text="Affichée sous les accroches, dans le bandeau d'accueil.")
    # Sans fichier, le site n'affiche pas de bouton de téléchargement
    cv = models.FileField(
        "CV (PDF)", upload_to='cv/', blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Facultatif. Le fichier est public : pas d'adresse postale ni de téléphone dedans.")

    def __str__(self):
        return self.name

    def tagline_list(self):
        return [line.strip() for line in self.taglines.splitlines() if line.strip()]

    def bio_paragraphs(self):
        return [line.strip() for line in self.bio.splitlines() if line.strip()]

    def meta_description(self):
        """Phrase reprise par les moteurs de recherche et par l'aperçu affiché quand le lien est partagé."""
        return self.lead or first_sentence(self.bio, limit=160)


class Formation(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    starting_date = models.DateField(null=True, blank=True)
    ending_date = models.DateField(null=True, blank=True)
    school = models.CharField("établissement", max_length=200, blank=True)

    def __str__(self):
        return self.title

    def years(self):
        """« 2021 – 2023 », ou une seule année, pour la frise."""
        years = dict.fromkeys(str(day.year) for day in (self.starting_date, self.ending_date) if day)
        return ' – '.join(years)


class Project(models.Model):
    class Status(models.TextChoices):
        IDEA = 'idea', 'Idée'
        IN_PROGRESS = 'in_progress', 'En cours'
        DONE = 'done', 'Terminé'

    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='projects/', blank=True, null=True)
    starting_date = models.DateField(null=True, blank=True)
    ending_date = models.DateField(null=True, blank=True)
    status = models.CharField("statut", max_length=20, choices=Status.choices, default=Status.DONE)
    # Phrase courte affichée sur la carte ; la description complète reste dans la modale
    summary = models.CharField("résumé", max_length=200, blank=True)
    repo_url = models.URLField("lien du dépôt", blank=True)
    demo_url = models.URLField("lien de la démo", blank=True)
    skills = models.ManyToManyField('Skill', verbose_name="technos", related_name='projects', blank=True)
    # Indépendant du statut : plusieurs projets peuvent être en cours sans tous occuper une carte large
    featured = models.BooleanField(
        "mis en avant", default=False,
        help_text="Affiche le projet en grand, en tête de la section Projets. Sans effet sur une idée.")

    # Forme du point dans le graphe du bandeau, et entrée de sa légende
    graph_kind = 'project'

    def __str__(self):
        return self.title

    @property
    def anchor(self):
        # Ancre de la carte dans la page, et clé du projet dans les données envoyées au script
        return f'projet-{self.pk}'

    @property
    def is_idea(self):
        return self.status == self.Status.IDEA

    def period(self):
        return period_label(self.starting_date, self.ending_date)

    def card_summary(self):
        return self.summary or first_sentence(self.description)

    def meta(self):
        return self.period()

    def links(self):
        candidates = (('Code', self.repo_url), ('Démo', self.demo_url))
        return [{'label': label, 'url': url} for label, url in candidates if url]


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Skill(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, related_name='skills', on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Experience(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='projects/', blank=True, null=True)
    starting_date = models.DateField(null=True, blank=True)
    ending_date = models.DateField(null=True, blank=True)
    company = models.CharField("entreprise", max_length=200, blank=True)
    # Phrase courte affichée sur la carte ; la description complète reste dans la modale
    summary = models.CharField("résumé", max_length=200, blank=True)
    skills = models.ManyToManyField(Skill, verbose_name="technos", related_name='experiences', blank=True)

    is_idea = False
    graph_kind = 'experience'

    def __str__(self):
        return self.title

    @property
    def anchor(self):
        # Ancre de l'expérience dans la page, et sa clé dans les données envoyées au script
        return f'experience-{self.pk}'

    def period(self):
        return period_label(self.starting_date, self.ending_date)

    def card_summary(self):
        return self.summary or first_sentence(self.description)

    def meta(self):
        return ' · '.join(part for part in (self.company, self.period()) if part)

    def links(self):
        return []