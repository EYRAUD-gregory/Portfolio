from django.core import mail
from django.test import TestCase, override_settings

from .models import Experience, Project, ProjectIdea


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


@override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class PagesTests(TestCase):
    def test_pages_render_with_empty_database(self):
        # Base vide : pas de Profile, aucune section remplie
        for url in ('/', '/politique-de-confidentialite/', '/mentions-legales/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_home_renders_items_without_image(self):
        # L'image est facultative : son absence ne doit pas faire tomber la page
        Project.objects.create(title='Projet sans image', description='Description')
        Experience.objects.create(title='Expérience sans image', description='Description')
        ProjectIdea.objects.create(title='Idée sans image', description='Description')

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Projet sans image')
        self.assertContains(response, 'Expérience sans image')
        self.assertContains(response, 'Idée sans image')
        self.assertNotContains(response, '<img src="/media/')
