from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0006_project_skills'),
    ]

    operations = [
        migrations.AddField(
            model_name='experience',
            name='company',
            field=models.CharField(blank=True, max_length=200, verbose_name='entreprise'),
        ),
        migrations.AddField(
            model_name='experience',
            name='summary',
            field=models.CharField(blank=True, max_length=200, verbose_name='résumé'),
        ),
        migrations.AddField(
            model_name='experience',
            name='skills',
            field=models.ManyToManyField(
                blank=True, related_name='experiences', to='portfolio.skill', verbose_name='technos'),
        ),
    ]
