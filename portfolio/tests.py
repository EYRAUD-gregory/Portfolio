from django.core import mail
from django.test import TestCase, override_settings

from .models import Project


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='portfolio@exemple.test',
    CONTACT_RECIPIENT='moi@exemple.test',
    # Pas de manifest collectstatic pendant les tests
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class ContactFormTests(TestCase):
    def test_visitor_address_is_only_reply_to(self):
        # cc_myself forgé à la main : il ne doit plus avoir aucun effet
        response = self.client.post('/', {
            'name': 'Visiteur',
            'sender': 'visiteur@exemple.test',
            'subject': 'Bonjour',
            'message': 'Un message',
            'cc_myself': 'on',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.recipients(), ['moi@exemple.test'])
        self.assertEqual(email.to, ['moi@exemple.test'])
        self.assertEqual(email.cc, [])
        self.assertEqual(email.bcc, [])
        self.assertEqual(email.from_email, 'portfolio@exemple.test')
        self.assertEqual(email.reply_to, ['visiteur@exemple.test'])


@override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class ProjectModalTests(TestCase):
    def test_description_is_html_escaped_in_data_attribute(self):
        # La modale lit cet attribut comme du texte : il doit porter la description
        # échappée pour le HTML, sans passer par escapejs / JSON.parse / innerHTML
        Project.objects.create(
            title='Projet',
            description='Ligne "un"\n<script>alert(1)</script>',
            image='projects/factice.png',
        )

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'data-description="Ligne &quot;un&quot;\n&lt;script&gt;alert(1)&lt;/script&gt;"',
        )
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertNotContains(response, 'u0022')
        # Une date absente ne doit pas s'afficher « None » dans la modale
        self.assertContains(response, 'data-start-date=""')
