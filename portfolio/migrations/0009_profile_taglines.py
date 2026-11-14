from django.db import migrations, models

# Textes jusqu'ici codés en dur dans script.js
FORMER_TAGLINES = "IA Générative & Agentique\nBases de données graphes\nPython\nGraphRAG"


def fill_taglines(apps, schema_editor):
    Profile = apps.get_model('portfolio', 'Profile')
    Profile.objects.filter(taglines='').update(taglines=FORMER_TAGLINES)


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0008_formation_school'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='taglines',
            field=models.TextField(
                blank=True, help_text='Une accroche par ligne.', verbose_name='accroches du bandeau'),
        ),
        migrations.RunPython(fill_taglines, migrations.RunPython.noop),
    ]
