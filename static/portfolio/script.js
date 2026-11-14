// Chaque bloc vérifie que ses éléments existent : le même script sert à la page d'accueil
// et aux pages légales, qui n'ont que la barre et le bouton de thème.
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const readJson = (id) => {
  const element = document.getElementById(id);
  return element ? JSON.parse(element.textContent) : null;
};

// Thème : suit le réglage du système, le bouton le remplace et le choix est retenu.
// Le nouveau thème s'étend en cercle depuis le bouton quand le navigateur le permet.
const themeButton = document.getElementById('theme-button');
if (themeButton) {
  themeButton.addEventListener('click', () => {
    const root = document.documentElement;
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    const apply = () => { root.dataset.theme = next; try { localStorage.setItem('theme', next); } catch (error) {} };
    if (reducedMotion || !document.startViewTransition) { apply(); return; }
    const box = themeButton.getBoundingClientRect();
    const x = box.left + box.width / 2, y = box.top + box.height / 2;
    // Sur téléphone, l'image de la page dépasse la fenêtre (barre d'adresse) : on vise la hauteur de l'écran
    const reachX = Math.max(x, Math.max(innerWidth, root.clientWidth) - x);
    const reachY = Math.max(y, Math.max(innerHeight, screen.height || 0) - y);
    const radius = Math.hypot(reachX, reachY) * 1.05;
    document.startViewTransition(apply).ready.then(() => {
      root.animate({ clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`] },
        { duration: 520, easing: 'cubic-bezier(.45, 0, .25, 1)', pseudoElement: '::view-transition-new(root)' });
    });
  });
}

// Menu mobile
const nav = document.getElementById('nav');
const menuButton = document.getElementById('menu-button');
const navLinks = document.getElementById('nav-links');
if (menuButton && navLinks) {
  const setMenu = (open) => {
    navLinks.classList.toggle('open', open);
    menuButton.setAttribute('aria-expanded', String(open));
  };
  menuButton.addEventListener('click', () => setMenu(!navLinks.classList.contains('open')));
  navLinks.addEventListener('click', () => setMenu(false));
}

// La barre est transparente tant qu'elle survole le bandeau rouge
const hero = document.getElementById('accueil');
if (nav && hero) {
  new IntersectionObserver(([entry]) => nav.classList.toggle('on-hero', entry.isIntersecting),
    { rootMargin: '-64px 0px 0px 0px' }).observe(hero);
}

// Un trait glisse sous le lien de la section en cours de lecture
const indicator = document.getElementById('nav-indicator');
if (navLinks && indicator) {
  let currentLink = null;
  const moveIndicator = () => {
    indicator.style.opacity = currentLink ? 1 : 0;
    if (!currentLink) return;
    indicator.style.width = `${currentLink.offsetWidth - 22}px`;
    indicator.style.transform = `translateX(${currentLink.offsetLeft + 11}px)`;
  };
  const spy = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      currentLink = navLinks.querySelector(`a[href="#${entry.target.id}"]`);
      for (const link of navLinks.querySelectorAll('a')) link.setAttribute('aria-current', String(link === currentLink));
      moveIndicator();
    }
  }, { rootMargin: '-45% 0px -50% 0px' });
  document.querySelectorAll('main > section[id]').forEach((section) => spy.observe(section));
  addEventListener('resize', moveIndicator);
}

// Apparition au défilement : chaque bloc arrive une fois, en cascade avec ses voisins
if (!reducedMotion) {
  const reveal = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add('in');
      reveal.unobserve(entry.target);
    }
  }, { rootMargin: '0px 0px -10% 0px' });
  document.querySelectorAll('[data-reveal]').forEach((element) => {
    const siblings = [...element.parentElement.children].filter((child) => child.hasAttribute('data-reveal'));
    element.style.setProperty('--i', siblings.indexOf(element) % 4);
    element.querySelectorAll('.tags li').forEach((tag, index) => tag.style.setProperty('--t', index));
    // Une fois arrivée, une carte retrouve ses propres transitions de survol
    if (element.matches('.card, .idea')) {
      element.addEventListener('transitionend', function done(event) {
        if (event.target !== element || event.propertyName !== 'transform') return;
        element.removeEventListener('transitionend', done);
        element.removeAttribute('data-reveal');
      });
    }
    reveal.observe(element);
  });
}

// Accroches saisies dans l'admin : elles s'écrivent et s'effacent tour à tour.
// Texte fixe (la première) si le visiteur a demandé moins d'animations.
const taglines = readJson('taglines') || [];
const tagline = document.getElementById('tagline');
if (tagline && !reducedMotion && taglines.length > 1) {
  let index = 0, length = taglines[0].length, erasing = true;
  const tick = () => {
    const text = taglines[index];
    length += erasing ? -1 : 1;
    tagline.textContent = text.slice(0, length);
    let delay = erasing ? 40 : 85;
    if (!erasing && length === text.length) { erasing = true; delay = 2400; }
    else if (erasing && length === 0) { erasing = false; index = (index + 1) % taglines.length; delay = 400; }
    setTimeout(tick, delay);
  };
  setTimeout(tick, 3200);
}

// Graphe du portfolio : moi → projets et expériences → technos.
// La disposition est calculée une fois ; ensuite les points flottent autour de leur place,
// se laissent attraper et tirent leurs voisins. Tout s'arrête dès que le bandeau sort de l'écran.
// On attend la police : la place réservée à chaque libellé dépend de sa largeur réelle.
const graphBox = document.getElementById('graph');
const graphData = readJson('graph-data');
if (graphBox && graphData && graphData.nodes.length > 1) document.fonts.ready.then(() => drawGraph(graphBox, graphData));

function drawGraph(box, data) {
  const NS = 'http://www.w3.org/2000/svg';
  const make = (name, attrs, parent) => {
    const element = document.createElementNS(NS, name);
    for (const key in attrs) element.setAttribute(key, attrs[key]);
    parent.append(element);
    return element;
  };
  const svg = make('svg', { role: 'group', 'aria-label': 'Graphe : mes projets et les technos qui les relient' }, box);
  const linkLayer = make('g', {}, svg), nodeLayer = make('g', {}, svg);
  const nodes = data.nodes, byId = new Map(nodes.map((node) => [node.id, node]));
  for (const node of nodes) node.near = new Set([node]);
  const links = data.links.map(([from, to]) => {
    const link = { from: byId.get(from), to: byId.get(to), line: make('line', {}, linkLayer) };
    link.from.near.add(link.to); link.to.near.add(link.from);
    return link;
  });

  let width = 0, height = 0, dragged = null, hovered = null, travelled = 0;
  // Au doigt : des cibles plus larges, et l'appui long n'ouvre pas le menu du navigateur
  const finger = matchMedia('(pointer: coarse)').matches;
  if (finger) svg.addEventListener('contextmenu', (event) => event.preventDefault());
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const local = (event) => {
    const rect = svg.getBoundingClientRect();
    return { x: (event.clientX - rect.left) * width / rect.width, y: (event.clientY - rect.top) * height / rect.height };
  };
  function highlight(target) {
    svg.classList.toggle('focus', !!target);
    for (const node of nodes) node.group.classList.toggle('on', !!target && target.near.has(node));
    for (const link of links) link.line.classList.toggle('on', !!target && (link.from === target || link.to === target));
  }

  nodes.forEach((node, index) => {
    node.degree = node.near.size - 1;
    node.r = node.type === 'me' ? 21 : node.type === 'item' ? 8.5 : 4;
    const parent = node.href ? make('a', { href: node.href, 'aria-label': node.full }, nodeLayer) : nodeLayer;
    const shared = node.type === 'tech' && node.degree > 1 ? ' shared' : '';
    node.group = make('g', { class: `node ${node.type}${node.idea ? ' sketch' : ''}${shared}` }, parent);
    make('circle', { class: 'hit', r: node.type === 'tech' ? (finger ? 18 : 13) : node.r + (finger ? 14 : 6) }, node.group);
    // Une expérience est un losange, tout le reste un disque : la légende sous le graphe le dit
    if (node.kind === 'experience') make('polygon', { points: '0,-10 10,0 0,10 -10,0' }, node.group);
    else make('circle', { r: node.r }, node.group);
    const label = make('text', { y: node.type === 'me' ? 4.5 : node.r + 14, 'text-anchor': 'middle' }, node.group);
    label.textContent = node.label;
    // Place réservée autour du point : son libellé compris, s'il est toujours affiché
    const labelled = node.type === 'item' || shared;
    node.half = labelled ? Math.max(node.r, label.getComputedTextLength() / 2) + 5 : node.r + 5;
    node.above = node.r + 5;
    node.below = labelled ? node.r + 21 : node.r + 5;
    // Flottement propre à chaque point
    node.float = node.type === 'me' ? 0 : node.type === 'item' ? 5 : node.degree > 1 ? 3.5 : 8;
    node.speedX = .35 + (index * 37 % 17) / 40; node.speedY = .3 + (index * 53 % 19) / 44;
    node.phase = index * 2.4;
    node.vx = node.vy = 0;

    node.group.addEventListener('pointerenter', () => { hovered = node; if (!dragged) highlight(node); });
    node.group.addEventListener('pointerleave', () => { hovered = null; if (!dragged) highlight(null); });
    if (node.href) {
      parent.addEventListener('focus', () => highlight(node));
      parent.addEventListener('blur', () => highlight(null));
      // Un point déplacé ne doit pas déclencher son lien
      parent.addEventListener('click', (event) => { if (travelled > 5) event.preventDefault(); });
    }
    if (reducedMotion) return;
    let grab = null, start = null;
    // Au doigt, le geste déplace le point : il ne fait pas défiler la page et ne sélectionne rien.
    // En contrepartie le navigateur n'émet plus de clic : l'ouverture du projet est faite au relâchement.
    node.group.addEventListener('touchstart', (event) => event.preventDefault(), { passive: false });
    node.group.addEventListener('pointerdown', (event) => {
      if (event.button) return;
      start = local(event); grab = { x: node.x - start.x, y: node.y - start.y };
      travelled = 0; dragged = node;
      node.group.setPointerCapture(event.pointerId);
      svg.classList.add('dragging'); highlight(node);
    });
    node.group.addEventListener('pointermove', (event) => {
      if (dragged !== node) return;
      const point = local(event);
      travelled = Math.max(travelled, Math.hypot(point.x - start.x, point.y - start.y));
      node.x = clamp(point.x + grab.x, 10, width - 10); node.y = clamp(point.y + grab.y, 10, height - 10);
    });
    const release = (event) => {
      if (dragged !== node) return;
      dragged = null; svg.classList.remove('dragging'); highlight(hovered);
      if (event.type === 'pointerup' && event.pointerType === 'touch' && travelled <= 5 && node.href) location.hash = node.href;
    };
    node.group.addEventListener('pointerup', release);
    node.group.addEventListener('pointercancel', release);
  });

  // Disposition : petite simulation de forces (répulsion, ressorts sur les liens, pas de chevauchement)
  function step(alpha) {
    const unit = Math.min(width, height) / 520;
    for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i], b = nodes[j];
      const dx = b.rx - a.rx || .01, dy = b.ry - a.ry || .01, d2 = dx * dx + dy * dy, d = Math.sqrt(d2);
      const both = a.type === 'tech' && b.type === 'tech';
      const push = (both ? 500 : a.type === 'tech' || b.type === 'tech' ? 1500 : 5200) * unit * unit / d2 * alpha;
      a.fx -= dx / d * push; a.fy -= dy / d * push; b.fx += dx / d * push; b.fy += dy / d * push;
    }
    for (const { from, to } of links) {
      const dx = to.rx - from.rx, dy = to.ry - from.ry, d = Math.hypot(dx, dy) || 1;
      const rest = (from.type === 'me' ? 190 : to.degree > 1 ? 120 : 46) * unit;
      const pull = (d - rest) / d * (to.degree > 1 ? .04 : .1) * alpha;
      from.fx += dx * pull; from.fy += dy * pull; to.fx -= dx * pull; to.fy -= dy * pull;
    }
    for (const node of nodes) {
      if (node.type === 'me') { node.rx = width / 2; node.ry = height / 2; continue; }
      // Rappel vers le centre, plus faible en largeur : le graphe s'étale dans son cadre
      node.fx = (node.fx + (width / 2 - node.rx) * .0012 * alpha) * .8;
      node.fy = (node.fy + (height / 2 - node.ry) * .004 * alpha) * .8;
      node.rx += node.fx; node.ry += node.fy;
    }
    // Ni les points ni leurs libellés ne se recouvrent : on écarte sur l'axe le moins engagé
    for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i], b = nodes[j], dx = b.rx - a.rx, dy = b.ry - a.ry;
      const overX = a.half + b.half - Math.abs(dx);
      const overY = (dy > 0 ? a.below + b.above : a.above + b.below) - Math.abs(dy);
      if (overX <= 0 || overY <= 0) continue;
      const moveA = a.type === 'me' ? 0 : b.type === 'me' ? 1 : .5, moveB = 1 - moveA;
      if (overX < overY) {
        const sign = dx >= 0 ? 1 : -1;
        a.rx -= sign * overX * moveA; b.rx += sign * overX * moveB;
      } else {
        const sign = dy >= 0 ? 1 : -1;
        a.ry -= sign * overY * moveA; b.ry += sign * overY * moveB;
      }
    }
    for (const node of nodes) {
      node.rx = clamp(node.rx, node.half + 6, width - node.half - 6); node.ry = clamp(node.ry, node.above + 6, height - node.below - 6);
    }
  }
  function layout() {
    width = box.clientWidth; height = box.clientHeight;
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    let seed = 29;  // tirage fixe : la même disposition à chaque visite
    const random = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
    for (const node of nodes) {
      const angle = random() * 6.283, distance = node.type === 'me' ? 0 : 20 + random() * 40;
      node.rx = width / 2 + Math.cos(angle) * distance; node.ry = height / 2 + Math.sin(angle) * distance;
      node.fx = node.fy = 0;
    }
    for (let i = 0; i < 320; i++) step(1 - i / 320 * .95);
  }
  function draw() {
    for (const { from, to, line } of links) {
      line.setAttribute('x1', from.x.toFixed(1)); line.setAttribute('y1', from.y.toFixed(1));
      line.setAttribute('x2', to.x.toFixed(1)); line.setAttribute('y2', to.y.toFixed(1));
    }
    for (const node of nodes) node.group.setAttribute('transform', `translate(${node.x.toFixed(1)} ${node.y.toFixed(1)})`);
  }
  const still = () => { for (const node of nodes) { node.x = node.rx; node.y = node.ry; } draw(); };

  layout();
  if (reducedMotion) {
    still();
  } else {
    // Au départ, tout est au centre : le graphe se déploie
    for (const node of nodes) { node.x = width / 2; node.y = height / 2; }
    let frame = 0, opened = 0;
    const animate = (now) => {
      opened = opened || now;
      const time = now / 1000;
      nodes.forEach((node, index) => {
        if (node === dragged) { node.vx = node.vy = 0; return; }
        // Déploiement décalé d'un point à l'autre
        const spread = clamp((now - opened - index * 22) / 900, 0, 1);
        let targetX = width / 2 + (node.rx - width / 2) * spread, targetY = height / 2 + (node.ry - height / 2) * spread;
        if (node !== hovered) {
          targetX += Math.sin(time * node.speedX + node.phase) * node.float * spread;
          targetY += Math.cos(time * node.speedY + node.phase) * node.float * spread;
        }
        // Un point attrapé entraîne ses voisins, d'autant plus qu'ils ne tiennent qu'à lui
        if (dragged && dragged.near.has(node)) {
          const follow = node.degree === 1 ? .8 : .3;
          targetX += (dragged.x - dragged.rx) * follow; targetY += (dragged.y - dragged.ry) * follow;
        }
        node.vx = (node.vx + (targetX - node.x) * .05) * .84;
        node.vy = (node.vy + (targetY - node.y) * .05) * .84;
        node.x += node.vx; node.y += node.vy;
      });
      draw();
      frame = requestAnimationFrame(animate);
    };
    // Le mouvement ne tourne que si le graphe est à l'écran et l'onglet visible
    let onScreen = false;
    const toggle = () => {
      cancelAnimationFrame(frame);
      if (onScreen && !document.hidden) frame = requestAnimationFrame(animate);
    };
    new IntersectionObserver(([entry]) => { onScreen = entry.isIntersecting; toggle(); }).observe(box);
    document.addEventListener('visibilitychange', toggle);
  }
  let lastWidth = box.clientWidth;
  new ResizeObserver(() => {
    if (Math.abs(box.clientWidth - lastWidth) < 40) return;
    lastWidth = box.clientWidth;
    layout();
    if (reducedMotion) still();
  }).observe(box);
}

// Affiche une description comme du texte. Seule exception : un lien <a href="http(s)://...">
// saisi dans l'admin est reconstruit en élément <a>, son libellé restant du texte.
function renderDescription(element, text) {
  const linkPattern = /<a\s+href="(https?:\/\/[^"\s]+)"[^>]*>([\s\S]*?)<\/a>/g;
  let lastIndex = 0;
  let match;

  element.textContent = '';
  while ((match = linkPattern.exec(text)) !== null) {
    element.append(text.slice(lastIndex, match.index));
    const link = document.createElement('a');
    link.href = match[1];
    link.textContent = match[2];
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    element.append(link);
    lastIndex = linkPattern.lastIndex;
  }
  element.append(text.slice(lastIndex));
}

// Fenêtre de détail : tout ce qui vient de la base est écrit en texte (textContent), jamais en HTML.
// Les retours à la ligne de la description sont rendus par le CSS (white-space: pre-line).
const dialog = document.getElementById('details');
const details = readJson('details-data');
if (dialog && details) {
  const part = (id) => document.getElementById(id);
  document.querySelectorAll('[data-open]').forEach((button) => button.addEventListener('click', () => {
    const item = details[button.dataset.open];
    if (!item) return;
    const image = part('d-img');
    image.hidden = !item.img;
    if (item.img) image.src = item.img; else image.removeAttribute('src');
    part('d-title').textContent = item.title;
    part('d-meta').textContent = item.meta;
    renderDescription(part('d-body'), item.body);
    part('d-tools').replaceChildren(...item.tools.map((tool) => Object.assign(document.createElement('li'), { textContent: tool })));
    part('d-links').replaceChildren(...item.links.filter((link) => /^https?:\/\//.test(link.url)).map((link) => Object.assign(
      document.createElement('a'),
      { className: 'link', href: link.url, target: '_blank', rel: 'noopener noreferrer', textContent: link.label + ' ↗' })));
    dialog.showModal();
    dialog.scrollTop = 0;
  }));
  dialog.querySelector('.dialog-close').addEventListener('click', () => dialog.close());
  // Un clic sur le fond, hors de la fenêtre, la referme
  dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
}

// Formulaire : le bouton d'envoi ne s'active qu'une fois la case de consentement cochée
const consent = document.getElementById('consent');
const submitButton = document.getElementById('submit-button');
if (consent && submitButton) {
  const sync = () => { submitButton.disabled = !consent.checked; };
  consent.addEventListener('change', sync);
  sync();
}
