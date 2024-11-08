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


class Project(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='projects/', blank=True, null=True)
    starting_date = models.DateTimeField(null=True, blank=True)
    ending_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title
