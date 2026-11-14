from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0003_merge_ideas_into_projects'),
    ]

    operations = [
        # Les idées ont été copiées dans Project par la migration précédente
        migrations.DeleteModel(
            name='ProjectIdea',
        ),
    ]
