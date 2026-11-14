from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0007_experience_company_summary_skills'),
    ]

    operations = [
        migrations.AddField(
            model_name='formation',
            name='school',
            field=models.CharField(blank=True, max_length=200, verbose_name='établissement'),
        ),
    ]
