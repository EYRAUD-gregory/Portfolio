from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0009_profile_taglines'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='featured',
            field=models.BooleanField(
                default=False,
                help_text='Affiche le projet en grand, en tête de la section Projets. Sans effet sur une idée.',
                verbose_name='mis en avant'),
        ),
    ]
