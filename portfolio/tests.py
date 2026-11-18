from datetime import date
from unittest import mock

import io
import urllib.error

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from . import antispam
from .graph import short_label
from .models import Category, Experience, Formation, Profile, Project, Skill


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='portfolio@exemple.test',
    CONTACT_RECIPIENT='moi@exemple.test',
    TURNSTILE_SITE_KEY='cle-publique-de-test',
    TURNSTILE_SECRET_KEY='cle-secrete-de-test',
    CONTACT_LIMIT_PER_IP_PER_HOUR=3,
    CONTACT_LIMIT_PER_DAY=50,
    # Aucune alerte réelle, même si le .env en configure une
    CONTACT_NTFY_URL='',
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
        self.assertNotContains(self.client.get('/'), 'class="elsewhere"')

        Profile.objects.create(
            name='Nom', bio='Bio', contact_email='moi@exemple.test',
            linkedin='https://www.linkedin.com/in/exemple/',
        )

        response = self.client.get('/')
        self.assertContains(response, 'class="elsewhere"')
        self.assertContains(response, 'href="https://www.linkedin.com/in/exemple/"')
        # Pas de lien GitHub tant que le profil n'en a pas
        self.assertNotContains(response, 'GitHub')

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

    def assert_alert_carries_nothing_from_the_visitor(self, request):
        sent = request.full_url + request.data.decode()
        for value in self.valid_data.values():
            if value != 'on':
                self.assertNotIn(value, sent)

    @override_settings(CONTACT_NTFY_URL='https://ntfy.exemple.test/sujet-de-test')
    def test_sent_message_triggers_an_alert_without_its_content(self):
        with mock.patch('portfolio.notify.urllib.request.urlopen') as urlopen:
            response = self.client.post('/', self.valid_data)

        self.assertEqual(response.status_code, 302)
        urlopen.assert_called_once()
        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.startswith('https://ntfy.exemple.test/sujet-de-test?'))
        self.assertIn('priority=default', request.full_url)
        self.assert_alert_carries_nothing_from_the_visitor(request)

    @override_settings(CONTACT_NTFY_URL='https://ntfy.exemple.test/sujet-de-test')
    def test_send_failure_triggers_a_high_priority_alert(self):
        with mock.patch('portfolio.views.EmailMessage.send', side_effect=OSError('SMTP injoignable')), \
                mock.patch('portfolio.notify.urllib.request.urlopen') as urlopen, \
                self.assertLogs('portfolio.views', level='ERROR'):
            self.client.post('/', self.valid_data)

        urlopen.assert_called_once()
        request = urlopen.call_args.args[0]
        self.assertIn('priority=high', request.full_url)
        self.assert_alert_carries_nothing_from_the_visitor(request)

    @override_settings(CONTACT_NTFY_URL='https://ntfy.exemple.test/sujet-de-test')
    def test_unreachable_ntfy_does_not_break_the_form(self):
        error = urllib.error.URLError('injoignable')
        with mock.patch('portfolio.notify.urllib.request.urlopen', side_effect=error), \
                self.assertLogs('portfolio.notify', level='WARNING') as logs:
            response = self.client.post('/', self.valid_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        # Le sujet ntfy fait office de secret : jamais dans les journaux
        self.assertNotIn('sujet-de-test', '\n'.join(logs.output))

    def test_no_alert_without_ntfy_address(self):
        with mock.patch('portfolio.notify.urllib.request.urlopen') as urlopen:
            self.client.post('/', self.valid_data)

        urlopen.assert_not_called()



@override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class ProjectModalTests(TestCase):
    def test_description_reaches_the_dialog_as_inert_json(self):
        # La fenêtre de détail lit la description dans un bloc JSON et l'écrit en texte.
        # json_script neutralise < > & : rien de ce qui est saisi ne peut fermer la balise
        # ni devenir du HTML, et aucun passage par escapejs / innerHTML.
        project = Project.objects.create(
            title='Projet <b>gras</b>',
            description='Ligne "un"\n</script><script>alert(1)</script>',
            image='projects/factice.png',
        )

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<script id="details-data" type="application/json">')
        self.assertContains(
            response,
            r'"body": "Ligne \"un\"\n\u003C/script\u003E\u003Cscript\u003Ealert(1)\u003C/script\u003E"',
        )
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertNotContains(response, '<b>gras</b>')
        # La description n'est écrite nulle part ailleurs dans la page
        self.assertNotContains(response, 'data-description')
        # Une date absente ne s'affiche pas « None »
        self.assertEqual(response.context['details'][project.anchor]['meta'], '')
        self.assertNotContains(response, 'None')


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

    def test_legal_pages_share_the_site_layout(self):
        Profile.objects.create(name='Prénom Nom', bio='Bio', contact_email='moi@exemple.test')

        for url in ('/politique-de-confidentialite/', '/mentions-legales/'):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, '/static/portfolio/styles.css')
                self.assertContains(response, '<span class="brand-mark">PN</span>')
                self.assertContains(response, 'id="theme-button"')
                self.assertNotContains(response, '<style')

    def test_privacy_policy_says_what_the_browser_keeps(self):
        # La page doit dire ce que fait le site : le thème choisi est mémorisé dans le navigateur
        response = self.client.get('/politique-de-confidentialite/')

        self.assertContains(response, 'stockage local de votre navigateur')

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

    def test_project_is_not_featured_by_default(self):
        # « Mis en avant » se choisit projet par projet, quel que soit le statut
        project = Project.objects.create(
            title='Projet', description='Description', status=Project.Status.IN_PROGRESS)

        self.assertFalse(project.featured)

        project.featured = True
        project.save()

        self.assertEqual([p.title for p in Project.objects.filter(featured=True)], ['Projet'])

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

    def test_formation_school_is_optional(self):
        formation = Formation(title='Diplôme', description='Description')
        formation.full_clean()
        formation.school = 'Université'
        formation.save()

        self.assertEqual(Formation.objects.get().school, 'Université')

    def test_items_without_date_come_last(self):
        for model in (Project, Formation, Experience):
            model.objects.create(title='Sans date', description='Description')
            model.objects.create(title='Ancien', description='Description', starting_date=date(2020, 1, 1))
            model.objects.create(title='Récent', description='Description', starting_date=date(2024, 1, 1))

        context = self.client.get('/').context

        for key in ('projects', 'formations', 'experiences'):
            with self.subTest(key=key):
                self.assertEqual([item.title for item in context[key]], ['Récent', 'Ancien', 'Sans date'])

    def test_taglines_come_from_the_profile(self):
        # Sans profil : une liste vide, le script n'a rien à afficher
        self.assertContains(self.client.get('/'), '<script id="taglines" type="application/json">[]</script>')

        Profile.objects.create(
            name='Nom', bio='Bio', contact_email='moi@exemple.test',
            taglines='Python\n\n  Django & <ASGI>  \n',
        )

        response = self.client.get('/')
        self.assertEqual(response.context['taglines'], ['Python', 'Django & <ASGI>'])
        # json_script neutralise les caractères qui pourraient fermer la balise
        self.assertNotContains(response, '<ASGI>')

    def test_profile_lead_is_optional(self):
        profile = Profile(name='Nom', bio='Bio', contact_email='moi@exemple.test')
        profile.full_clean()

        profile.lead = 'x' * 301
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_profile_cv_is_optional_and_must_be_a_pdf(self):
        profile = Profile(name='Nom', bio='Bio', contact_email='moi@exemple.test')
        profile.full_clean()
        self.assertFalse(profile.cv)

        profile.cv = SimpleUploadedFile('cv.pdf', b'%PDF-1.4')
        profile.full_clean()

        profile.cv = SimpleUploadedFile('cv.html', b'<script>alert(1)</script>')
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_ideas_have_their_own_block(self):
        Project.objects.create(title='Terminé', description='Description')
        Project.objects.create(title='Commencé', description='Description', status=Project.Status.IN_PROGRESS)
        Project.objects.create(title='Idée', description='Description', status=Project.Status.IDEA)

        response = self.client.get('/')

        self.assertCountEqual([p.title for p in response.context['projects']], ['Terminé', 'Commencé'])
        self.assertEqual([p.title for p in response.context['project_ideas']], ['Idée'])
        # Le témoin « En cours » n'apparaît que sur le projet commencé
        self.assertContains(response, 'class="status"', count=1)

    def test_featured_projects_come_first_on_a_wide_card(self):
        Project.objects.create(title='Récent', description='Description', starting_date=date(2024, 1, 1))
        Project.objects.create(
            title='Ancien mis en avant', description='Description', starting_date=date(2020, 1, 1), featured=True)
        # Sans effet sur une idée : elle reste dans son bloc
        Project.objects.create(title='Idée', description='Description', status=Project.Status.IDEA, featured=True)

        response = self.client.get('/')

        self.assertEqual([p.title for p in response.context['projects']], ['Ancien mis en avant', 'Récent'])
        self.assertContains(response, 'class="card wide"', count=1)

    def test_card_summary_falls_back_on_the_first_sentence(self):
        # Tant que le résumé n'est pas saisi : première phrase de la description, sans balise de lien
        project = Project(
            title='Projet',
            description='Un <a href="https://exemple.test">outil</a>\nde tri. Puis la suite. Et la fin.')
        self.assertEqual(project.card_summary(), 'Un outil de tri.')

        project.summary = 'Résumé saisi'
        self.assertEqual(project.card_summary(), 'Résumé saisi')
        # Une phrase trop longue est coupée sur un mot entier
        long_summary = Project(title='Projet', description='abcdefg ' * 60).card_summary()
        self.assertEqual(long_summary, 'abcdefg ' * 23 + 'abcdefg…')

    def test_header_shows_lead_and_cv_only_when_filled(self):
        profile = Profile.objects.create(name='Prénom Nom', bio='Un\n\nDeux', contact_email='moi@exemple.test')

        response = self.client.get('/')
        self.assertNotContains(response, 'class="hero-lead"')
        self.assertNotContains(response, 'Télécharger le CV')
        self.assertContains(response, '<span class="brand-mark">PN</span>')
        self.assertContains(response, '<p>Un</p><p>Deux</p>')

        profile.lead = 'Une phrase de présentation'
        profile.cv = 'cv/cv.pdf'
        profile.save()

        response = self.client.get('/')
        self.assertContains(response, '<p class="hero-lead">Une phrase de présentation</p>')
        self.assertContains(response, 'href="/media/cv/cv.pdf" download')

    def test_share_preview_uses_absolute_addresses(self):
        # Sans profil : pas de description vide, mais l'image et l'adresse sont là
        response = self.client.get('/')
        self.assertNotContains(response, 'name="description"')
        self.assertContains(response, '<meta property="og:url" content="http://testserver/">')
        self.assertContains(
            response, '<meta property="og:image" content="http://testserver/static/images/partage.jpeg">')

        profile = Profile.objects.create(
            name='Prénom Nom', bio='Première phrase de la bio. La suite.', contact_email='moi@exemple.test')
        response = self.client.get('/')
        self.assertContains(response, '<meta property="og:title" content="Prénom Nom - Portfolio">')
        self.assertContains(response, '<meta name="description" content="Première phrase de la bio.">')

        # La phrase de présentation, une fois saisie, remplace le début de la bio
        profile.lead = 'Phrase de "présentation" <b>'
        profile.save()
        self.assertContains(
            self.client.get('/'),
            '<meta property="og:description" content="Phrase de &quot;présentation&quot; &lt;b&gt;">')

    def test_graph_is_drawn_only_when_there_is_something_to_link(self):
        # Base vide : pas de cadre vide dans le bandeau, pas de section sans contenu
        response = self.client.get('/')
        self.assertNotContains(response, 'id="graph"')
        for section in ('a-propos', 'experiences', 'competences', 'projets', 'parcours'):
            self.assertNotContains(response, f'id="{section}"')
        self.assertContains(response, 'id="contact"')

        project = Project.objects.create(title='Projet', description='Description')
        response = self.client.get('/')
        self.assertContains(response, 'id="graph"')
        # La légende ne nomme que ce que le graphe montre : ni techno, ni expérience, ni idée ici
        self.assertNotContains(response, 'UTILISE')
        self.assertEqual([entry['key'] for entry in response.context['graph_legend']], ['me', 'project'])
        self.assertContains(response, '<li><i class="key-project"></i>projet</li>')
        self.assertNotContains(response, 'key-tech')

        project.skills.add(Skill.objects.create(name='Python', category=Category.objects.create(name='Langages')))
        Experience.objects.create(title='Poste', description='Description')
        Project.objects.create(title='Idée', description='Description', status=Project.Status.IDEA)
        response = self.client.get('/')
        self.assertContains(response, 'UTILISE')
        self.assertEqual(
            [entry['label'] for entry in response.context['graph_legend']],
            ['moi', 'expérience', 'projet', 'idée', 'techno'])

    def test_formation_years(self):
        self.assertEqual(Formation(starting_date=date(2021, 9, 1), ending_date=date(2023, 6, 30)).years(), '2021 – 2023')
        self.assertEqual(Formation(starting_date=date(2021, 1, 1), ending_date=date(2021, 6, 30)).years(), '2021')
        self.assertEqual(Formation().years(), '')

    def test_home_loads_no_third_party_stylesheet_or_font(self):
        # Feuilles de style, police et icônes sont servies par le site lui-même
        response = self.client.get('/')

        for host in ('w3schools.com', 'googleapis.com', 'gstatic.com', 'cdnjs.cloudflare.com'):
            with self.subTest(host=host):
                self.assertNotContains(response, host)
        for path in ('/static/portfolio/styles.css', '/static/portfolio/theme.js', '/static/portfolio/script.js',
                     '/static/vendor/montserrat/montserrat-latin.woff2'):
            with self.subTest(path=path):
                self.assertContains(response, path)
        # Les anciennes feuilles et icônes tierces ne sont plus référencées
        self.assertNotContains(response, 'w3.css')
        self.assertNotContains(response, 'w3-')
        self.assertNotContains(response, 'font-awesome')
        # Aucun style ni script écrit dans la page : une politique de sécurité stricte reste possible
        self.assertNotContains(response, '<style')
        self.assertNotContains(response, ' style="')
        self.assertNotContains(response, '<script>')


@override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class GraphDataTests(TestCase):
    def setUp(self):
        languages = Category.objects.create(name='Langages')
        self.python = Skill.objects.create(name='Python', category=languages)
        self.neo4j = Skill.objects.create(name='Neo4j', category=languages)

    def test_graph_links_me_to_items_and_items_to_their_skills(self):
        Profile.objects.create(name='Prénom Nom', bio='Bio', contact_email='moi@exemple.test')
        experience = Experience.objects.create(title='Poste', description='Description')
        project = Project.objects.create(title='Projet', description='Description')
        idea = Project.objects.create(title='Idée', description='Description', status=Project.Status.IDEA)
        experience.skills.add(self.python)
        project.skills.add(self.python, self.neo4j)

        graph = self.client.get('/').context['graph']

        nodes = {node['id']: node for node in graph['nodes']}
        self.assertEqual(nodes['me']['label'], 'PN')
        self.assertEqual(nodes[project.anchor]['href'], f'#projet-{project.pk}')
        self.assertEqual(nodes[experience.anchor]['href'], f'#experience-{experience.pk}')
        self.assertTrue(nodes[idea.anchor]['idea'])
        self.assertFalse(nodes[project.anchor]['idea'])
        # Une expérience et un projet n'ont pas la même forme dans le graphe
        self.assertEqual(nodes[experience.anchor]['kind'], 'experience')
        self.assertEqual(nodes[project.anchor]['kind'], 'project')
        # Python sert à deux éléments : un seul point, deux liens
        self.assertEqual([n['label'] for n in graph['nodes'] if n['type'] == 'tech'], ['Python', 'Neo4j'])
        self.assertCountEqual(graph['links'], [
            ['me', experience.anchor], ['me', project.anchor], ['me', idea.anchor],
            [experience.anchor, 'tech:python'], [project.anchor, 'tech:python'], [project.anchor, 'tech:neo4j'],
        ])

    def test_same_skill_entered_twice_is_one_point(self):
        other = Skill.objects.create(name=' python ', category=Category.objects.create(name='Outils'))
        project = Project.objects.create(title='Projet', description='Description')
        project.skills.add(self.python, other)

        graph = self.client.get('/').context['graph']

        self.assertEqual([n['id'] for n in graph['nodes']], ['me', project.anchor, 'tech:python'])
        self.assertEqual(graph['links'], [['me', project.anchor], [project.anchor, 'tech:python']])

    def test_graph_is_only_me_with_an_empty_database(self):
        graph = self.client.get('/').context['graph']

        self.assertEqual(graph, {'nodes': [{'id': 'me', 'type': 'me', 'label': ''}], 'links': []})

    def test_long_titles_are_shortened_on_whole_words(self):
        self.assertEqual(short_label('Titre court'), 'Titre court')
        self.assertEqual(short_label('Assistant de recherche pour les archives'), 'Assistant de recherche…')
        # Pas de coupe sur un petit mot : « Guide de… » ne veut rien dire
        self.assertEqual(short_label('Classification de documents juridiques'), 'Classification…')

    def test_details_carry_what_the_dialog_shows(self):
        experience = Experience.objects.create(
            title='Poste', description='Le détail', company='Entreprise',
            starting_date=date(2023, 9, 1), ending_date=date(2024, 6, 30))
        project = Project.objects.create(
            title='Projet', description='Ligne "un"\n<b>deux</b>', image='projects/factice.png',
            starting_date=date(2022, 3, 1), ending_date=date(2022, 3, 20),
            repo_url='https://exemple.test/depot', demo_url='https://exemple.test/demo')
        project.skills.add(self.neo4j, self.python)

        details = self.client.get('/').context['details']

        self.assertEqual(details[experience.anchor], {
            'title': 'Poste', 'meta': 'Entreprise · septembre 2023 – juin 2024', 'body': 'Le détail',
            'tools': [], 'links': [], 'img': '',
        })
        self.assertEqual(details[project.anchor], {
            'title': 'Projet', 'meta': 'mars 2022', 'body': 'Ligne "un"\n<b>deux</b>',
            'tools': ['Neo4j', 'Python'],
            'links': [{'label': 'Code', 'url': 'https://exemple.test/depot'},
                      {'label': 'Démo', 'url': 'https://exemple.test/demo'}],
            'img': '/media/projects/factice.png',
        })


@override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class ProfileAdminTests(TestCase):
    def test_a_second_profile_cannot_be_added(self):
        self.client.force_login(User.objects.create_superuser('admin'))
        add_url = reverse('admin:portfolio_profile_add')

        self.assertEqual(self.client.get(add_url).status_code, 200)

        Profile.objects.create(name='Nom', bio='Bio', contact_email='moi@exemple.test')

        with self.assertLogs('django.request', level='WARNING'):
            self.assertEqual(self.client.get(add_url).status_code, 403)


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
