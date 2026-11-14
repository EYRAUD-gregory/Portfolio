from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='status',
            field=models.CharField(
                choices=[('idea', 'Idée'), ('in_progress', 'En cours'), ('done', 'Terminé')],
                default='done',
                max_length=20,
                verbose_name='statut',
            ),
        ),
    ]
