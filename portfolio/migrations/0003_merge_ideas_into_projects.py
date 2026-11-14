from django.db import migrations


def copy_ideas_to_projects(apps, schema_editor):
    # Chaque idée devient un projet au statut « idée ». La table des idées n'est pas
    # touchée ici : elle est supprimée par la migration suivante. Le chemin de l'image
    # est repris tel quel, le fichier ne bouge pas.
    Project = apps.get_model('portfolio', 'Project')
    ProjectIdea = apps.get_model('portfolio', 'ProjectIdea')
    for idea in ProjectIdea.objects.order_by('pk'):
        Project.objects.create(
            title=idea.title,
            description=idea.description,
            image=idea.image,
            status='idea',
        )


def remove_copied_projects(apps, schema_editor):
    # Retour arrière : ne retire que les projets « idée » dont l'idée d'origine existe encore
    Project = apps.get_model('portfolio', 'Project')
    ProjectIdea = apps.get_model('portfolio', 'ProjectIdea')
    for idea in ProjectIdea.objects.all():
        Project.objects.filter(status='idea', title=idea.title, description=idea.description).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0002_project_status'),
    ]

    operations = [
        migrations.RunPython(copy_ideas_to_projects, remove_copied_projects),
    ]
