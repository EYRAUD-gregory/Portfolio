from django.db import models

# Create your models here.
# portfolio/models.py
from django.db import models


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

    def __str__(self):
        return self.name

    def tagline_list(self):
        return [line.strip() for line in self.taglines.splitlines() if line.strip()]


class Formation(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    starting_date = models.DateField(null=True, blank=True)
    ending_date = models.DateField(null=True, blank=True)
    school = models.CharField("établissement", max_length=200, blank=True)

    def __str__(self):
        return self.title


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

    def __str__(self):
        return self.title


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

    def __str__(self):
        return self.title