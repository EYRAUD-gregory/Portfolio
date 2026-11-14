import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0011_profile_lead'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='cv',
            field=models.FileField(
                blank=True,
                help_text="Facultatif. Le fichier est public : pas d'adresse postale ni de téléphone dedans.",
                upload_to='cv/',
                validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf'])],
                verbose_name='CV (PDF)'),
        ),
    ]
