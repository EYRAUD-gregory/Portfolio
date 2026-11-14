from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0005_project_summary_and_links'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='skills',
            field=models.ManyToManyField(
                blank=True, related_name='projects', to='portfolio.skill', verbose_name='technos'),
        ),
    ]
