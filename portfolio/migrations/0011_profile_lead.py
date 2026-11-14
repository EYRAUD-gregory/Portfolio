from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0010_project_featured'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='lead',
            field=models.CharField(
                blank=True, help_text="Affichée sous les accroches, dans le bandeau d'accueil.",
                max_length=300, verbose_name='phrase de présentation'),
        ),
    ]
