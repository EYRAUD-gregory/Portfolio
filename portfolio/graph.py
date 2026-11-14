"""Données transmises à la page d'accueil en JSON : le graphe du bandeau et la fenêtre de détail.

Rien ici ne produit de HTML : la page reçoit des valeurs, le script les écrit comme du texte.
"""

# Mots sur lesquels un libellé raccourci ne doit pas s'arrêter (« Guide de… »)
SMALL_WORDS = {'de', 'du', 'des', 'la', 'le', 'les', 'pour', 'en', 'et', 'à', 'au', 'aux', 'un', 'une'}


def short_label(title, limit=22):
    """Titre raccourci à des mots entiers, pour tenir sous un point du graphe."""
    if len(title) <= limit:
        return title
    kept = []
    for word in title.split():
        if len(' '.join(kept + [word])) > limit:
            break
        kept.append(word)
    while kept and kept[-1].lower() in SMALL_WORDS:
        kept.pop()
    return (' '.join(kept) or title[:limit]) + '…'


def initials(name):
    """« Prénom Nom » → « PN », affiché dans le point central et dans la barre."""
    return ''.join(word[0] for word in name.split()[:2]).upper()


def build_graph(profile, items):
    """Moi → expériences et projets → technos. Une techno partagée n'a qu'un point."""
    nodes = [{'id': 'me', 'type': 'me', 'label': initials(profile.name) if profile else ''}]
    links = []
    known_techs = set()
    for item in items:
        nodes.append({
            'id': item.anchor,
            'type': 'item',
            # Expérience ou projet : le point n'a pas la même forme
            'kind': item.graph_kind,
            'idea': item.is_idea,
            'label': short_label(item.title),
            'full': item.title,
            'href': '#' + item.anchor,
        })
        links.append(['me', item.anchor])
        linked = set()
        for skill in item.skills.all():
            # Rapprochées par leur nom : la même techno saisie deux fois ne fait pas deux points
            tech = 'tech:' + skill.name.strip().lower()
            if tech in linked:
                continue
            linked.add(tech)
            if tech not in known_techs:
                known_techs.add(tech)
                nodes.append({'id': tech, 'type': 'tech', 'label': skill.name.strip()})
            links.append([item.anchor, tech])
    return {'nodes': nodes, 'links': links}


# Entrées de la légende, dans l'ordre du graphe : du centre vers l'extérieur
LEGEND = (('me', 'moi'), ('experience', 'expérience'), ('project', 'projet'), ('idea', 'idée'), ('tech', 'techno'))


def build_legend(graph):
    """La légende ne nomme que ce que le graphe montre."""
    present = {'idea' if node.get('idea') else node.get('kind', node['type']) for node in graph['nodes']}
    return [{'key': key, 'label': label} for key, label in LEGEND if key in present]


def build_details(items):
    """Contenu de la fenêtre de détail, par ancre de carte."""
    return {
        item.anchor: {
            'title': item.title,
            'meta': item.meta(),
            'body': item.description,
            'tools': [skill.name for skill in item.skills.all()],
            'links': item.links(),
            'img': item.image.url if item.image else '',
        }
        for item in items
    }
