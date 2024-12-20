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

    def __str__(self):
        return self.name


class Formation(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    starting_date = models.DateField(null=True, blank=True)
    ending_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.title


class Project(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='projects/', blank=True, null=True)
    starting_date = models.DateField(null=True, blank=True)
    ending_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.title


class ProjectIdea(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='projects_ideas/', blank=True, null=True)

    def __str__(self):
        return self.title

    def convert_to_project(self, starting_date, ending_date):
        """
        Convertit cette idée en un projet en cours ou terminé.
        """
        project = Project.objects.create(
            title=self.title,
            description=self.description,
            image=self.image,
            starting_date=starting_date,
            ending_date=ending_date
        )
        return project


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
