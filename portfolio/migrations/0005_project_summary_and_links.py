from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0004_delete_projectidea'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='summary',
            field=models.CharField(blank=True, max_length=200, verbose_name='résumé'),
        ),
        migrations.AddField(
            model_name='project',
            name='repo_url',
            field=models.URLField(blank=True, verbose_name='lien du dépôt'),
        ),
        migrations.AddField(
            model_name='project',
            name='demo_url',
            field=models.URLField(blank=True, verbose_name='lien de la démo'),
        ),
    ]
