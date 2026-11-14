from unittest import mock

import io
import urllib.error

from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings

from . import antispam
from .models import Category, Experience, Formation, Profile, Project, Skill


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='portfolio@exemple.test',
    CONTACT_RECIPIENT='moi@exemple.test',
    TURNSTILE_SITE_KEY='cle-publique-de-test',
    TURNSTILE_SECRET_KEY='cle-secrete-de-test',
    CONTACT_LIMIT_PER_IP_PER_HOUR=3,
    CONTACT_LIMIT_PER_DAY=50,
    # Pas de manifest collectstatic pendant les tests
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class ContactFormTests(TestCase):
    valid_data = {
        'name': 'Visiteur',
        'sender': 'visiteur@exemple.test',
        'subject': 'Bonjour',
        'message': 'Un message',
        'consent': 'on',
    }

    def setUp(self):
        # Compteurs remis à zéro, et Turnstile simulé : aucun test n'appelle Cloudflare
        cache.clear()
        patcher = mock.patch('portfolio.antispam.verify_turnstile', return_value=True)
        self.verify_turnstile = patcher.start()
        self.addCleanup(patcher.stop)

    def test_turnstile_refusal_blocks_sending(self):
        self.verify_turnstile.return_value = False

        response = self.client.post('/', {**self.valid_data, 'cf-turnstile-response': 'jeton'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(response, 'La vérification anti-robot a échoué.')
        self.verify_turnstile.assert_called_once_with('jeton', '127.0.0.1')

    def test_limit_per_address(self):
        # 3 envois par heure et par adresse (valeur par défaut), l'adresse venant de Cloudflare
        for _ in range(3):
            self.assertEqual(self.client.post('/', self.valid_data, HTTP_CF_CONNECTING_IP='203.0.113.7').status_code, 302)

        blocked = self.client.post('/', self.valid_data, HTTP_CF_CONNECTING_IP='203.0.113.7')
        other = self.client.post('/', self.valid_data, HTTP_CF_CONNECTING_IP='203.0.113.8')

        self.assertContains(blocked, 'Trop de messages ont été envoyés.')
        self.assertEqual(other.status_code, 302)
        self.assertEqual(len(mail.outbox), 4)

    @override_settings(CONTACT_LIMIT_PER_DAY=1)
    def test_daily_limit_applies_to_every_address(self):
        self.client.post('/', self.valid_data, HTTP_CF_CONNECTING_IP='203.0.113.7')

        response = self.client.post('/', self.valid_data, HTTP_CF_CONNECTING_IP='203.0.113.8')

        self.assertContains(response, 'Trop de messages ont été envoyés.')
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(CONTACT_LIMIT_PER_DAY=1)
    def test_refused_robots_do_not_use_up_the_daily_limit(self):
        self.verify_turnstile.return_value = False
        self.client.post('/', self.valid_data, HTTP_CF_CONNECTING_IP='203.0.113.7')
        self.verify_turnstile.return_value = True

        response = self.client.post('/', self.valid_data, HTTP_CF_CONNECTING_IP='203.0.113.8')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

    def test_widget_is_rendered_with_the_site_key(self):
        response = self.client.get('/')

        self.assertContains(response, 'class="cf-turnstile" data-sitekey="cle-publique-de-test"')
        self.assertNotContains(response, 'cle-secrete-de-test')

    def test_success_redirects_to_contact_section_with_confirmation(self):
        response = self.client.post('/', self.valid_data, follow=True)

        # Redirection après POST, vers l'ancre du formulaire
        self.assertEqual(response.redirect_chain, [('/#contact', 302)])
        self.assertContains(response, 'Votre message a été envoyé avec succès !')
        self.assertEqual(len(mail.outbox), 1)

    def test_consent_is_required_server_side(self):
        data = {k: v for k, v in self.valid_data.items() if k != 'consent'}

        response = self.client.post('/', data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(response, 'Vous devez accepter la politique de confidentialité.')
        # Les champs déjà saisis sont conservés
        self.assertContains(response, 'value="visiteur@exemple.test"')

    def test_subject_cannot_inject_mail_headers(self):
        data = {**self.valid_data, 'subject': 'Bonjour\r\nBcc: victime@exemple.test'}

        self.client.post('/', data)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, 'Bonjour Bcc: victime@exemple.test')
        self.assertEqual(email.recipients(), ['moi@exemple.test'])

    def test_send_failure_shows_error_instead_of_500(self):
        with mock.patch('portfolio.views.EmailMessage.send', side_effect=OSError('SMTP injoignable')):
            with self.assertLogs('portfolio.views', level='ERROR'):
                response = self.client.post('/', self.valid_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Votre message n&#x27;a pas pu être envoyé.")
        self.assertNotContains(response, 'Votre message a été envoyé avec succès !')

    def test_company_and_phone_are_no_longer_collected(self):
        # Champs retirés : forgés à la main, ils ne doivent pas arriver dans le mail
        response = self.client.post('/', {**self.valid_data, 'societe': 'Entreprise forgée', 'telephone': '0102030405'})

        self.assertEqual(response.status_code, 302)
        body = mail.outbox[0].body
        self.assertNotIn('Entreprise forgée', body)
        self.assertNotIn('0102030405', body)
        self.assertNotIn('Société', body)
        self.assertNotIn('Téléphone', body)
        page = self.client.get('/')
        self.assertNotContains(page, 'name="societe"')
        self.assertNotContains(page, 'name="telephone"')

    def test_linkedin_link_is_shown_next_to_the_form(self):
        self.assertNotContains(self.client.get('/'), 'class="contact-alternative"')

        Profile.objects.create(
            name='Nom', bio='Bio', contact_email='moi@exemple.test',
            linkedin='https://www.linkedin.com/in/exemple/',
        )

        response = self.client.get('/')
        self.assertContains(response, 'class="contact-alternative"')
        self.assertContains(response, 'href="https://www.linkedin.com/in/exemple/"')

    def test_visitor_address_is_only_reply_to(self):
        # cc_myself forgé à la main : il ne doit plus avoir aucun effet
        response = self.client.post('/', {**self.valid_data, 'cc_myself': 'on'})

        self.assertEqual(response.status_code, 302)
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
        Project.objects.create(title='Idée sans image', description='Description', status=Project.Status.IDEA)

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Projet sans image')
        self.assertContains(response, 'Expérience sans image')
        self.assertContains(response, 'Idée sans image')
        self.assertNotContains(response, '<img src="/media/')

    def test_project_is_done_by_default(self):
        # Les projets saisis avant l'ajout du statut restent « terminés »
        project = Project.objects.create(title='Projet', description='Description')

        self.assertEqual(project.status, Project.Status.DONE)
        self.assertEqual(project.get_status_display(), 'Terminé')

    def test_project_summary_and_links_are_optional(self):
        project = Project(title='Projet', description='Description')
        project.full_clean()

        project.repo_url = 'pas une adresse'
        with self.assertRaises(ValidationError):
            project.full_clean()

    def test_projects_can_be_found_by_skill(self):
        python = Skill.objects.create(name='Python', category=Category.objects.create(name='Langages'))
        project = Project.objects.create(title='Projet', description='Description')
        Project.objects.create(title='Autre projet', description='Description')
        project.skills.add(python)

        self.assertEqual([p.title for p in python.projects.all()], ['Projet'])

    def test_experience_company_summary_and_skills_are_optional(self):
        python = Skill.objects.create(name='Python', category=Category.objects.create(name='Langages'))
        experience = Experience(title='Poste', description='Description')
        experience.full_clean()
        experience.company = 'Entreprise'
        experience.save()
        experience.skills.add(python)

        self.assertEqual([e.company for e in python.experiences.all()], ['Entreprise'])

    def test_unfinished_projects_go_to_the_ideas_section(self):
        Project.objects.create(title='Terminé', description='Description')
        Project.objects.create(title='En cours', description='Description', status=Project.Status.IN_PROGRESS)
        Project.objects.create(title='Idée', description='Description', status=Project.Status.IDEA)

        context = self.client.get('/').context

        self.assertEqual([p.title for p in context['projects']], ['Terminé'])
        self.assertCountEqual([p.title for p in context['project_ideas']], ['En cours', 'Idée'])

    def test_home_loads_no_third_party_stylesheet_or_font(self):
        # Feuilles de style, police et icônes sont servies par le site lui-même
        response = self.client.get('/')

        for host in ('w3schools.com', 'googleapis.com', 'gstatic.com', 'cdnjs.cloudflare.com'):
            with self.subTest(host=host):
                self.assertNotContains(response, host)
        self.assertContains(response, '/static/vendor/font-awesome/icons.svg#home')


class MergeIdeasMigrationTests(TransactionTestCase):
    before = [('portfolio', '0002_project_status')]
    after = [('portfolio', '0003_merge_ideas_into_projects')]

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        return MigrationExecutor(connection).loader.project_state(targets).apps

    def test_ideas_become_projects_with_idea_status(self):
        # Le schéma est ramené à la dernière migration à la fin du test
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(
            MigrationExecutor(connection).loader.graph.leaf_nodes()))
        apps = self.migrate(self.before)
        apps.get_model('portfolio', 'Project').objects.create(title='Projet existant', description='Déjà là')
        apps.get_model('portfolio', 'ProjectIdea').objects.create(
            title='Une idée', description='Sa description', image='projects_ideas/idee.png')

        apps = self.migrate(self.after)

        projects = {p.title: p for p in apps.get_model('portfolio', 'Project').objects.all()}
        self.assertEqual(set(projects), {'Projet existant', 'Une idée'})
        self.assertEqual(projects['Projet existant'].status, 'done')
        self.assertEqual(projects['Une idée'].status, 'idea')
        self.assertEqual(projects['Une idée'].description, 'Sa description')
        self.assertEqual(projects['Une idée'].image.name, 'projects_ideas/idee.png')

        # Retour arrière : seul le projet issu de l'idée est retiré
        apps = self.migrate(self.before)
        self.assertEqual(
            [p.title for p in apps.get_model('portfolio', 'Project').objects.all()], ['Projet existant'])


@override_settings(TURNSTILE_SITE_KEY='cle-publique-de-test', TURNSTILE_SECRET_KEY='cle-secrete-de-test')
class TurnstileVerificationTests(SimpleTestCase):
    def answer(self, body):
        return mock.patch('portfolio.antispam.urllib.request.urlopen', return_value=io.BytesIO(body))

    def test_accepts_only_an_explicit_success(self):
        with self.answer(b'{"success": true}') as urlopen:
            self.assertTrue(antispam.verify_turnstile('jeton', '203.0.113.7'))
        # Seuls ces trois champs partent chez Cloudflare
        self.assertEqual(
            urlopen.call_args.kwargs['data'],
            b'secret=cle-secrete-de-test&response=jeton&remoteip=203.0.113.7',
        )
        with self.answer(b'{"success": false, "error-codes": ["invalid-input-response"]}'):
            self.assertFalse(antispam.verify_turnstile('jeton', '203.0.113.7'))
        with self.answer(b'pas du JSON'), self.assertLogs('portfolio.antispam', level='ERROR'):
            self.assertFalse(antispam.verify_turnstile('jeton', '203.0.113.7'))

    def test_missing_token_is_refused_without_calling_cloudflare(self):
        with self.answer(b'{"success": true}') as urlopen:
            self.assertFalse(antispam.verify_turnstile('', '203.0.113.7'))
        urlopen.assert_not_called()

    def test_unreachable_service_is_a_refusal(self):
        error = urllib.error.URLError('injoignable')
        with mock.patch('portfolio.antispam.urllib.request.urlopen', side_effect=error):
            with self.assertLogs('portfolio.antispam', level='ERROR'):
                self.assertFalse(antispam.verify_turnstile('jeton', '203.0.113.7'))

    @override_settings(TURNSTILE_SITE_KEY='', TURNSTILE_SECRET_KEY='')
    def test_missing_keys_are_a_refusal_outside_debug(self):
        with self.assertLogs('portfolio.antispam', level='ERROR'):
            self.assertFalse(antispam.verify_turnstile('jeton', '203.0.113.7'))
        with override_settings(DEBUG=True):
            self.assertTrue(antispam.verify_turnstile('jeton', '203.0.113.7'))
