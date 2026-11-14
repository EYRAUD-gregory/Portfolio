/* Animation de l'écriture des postes
    Ritch Rivia: https://www.youtube.com/watch?v=161yxE3-00o&ab_channel=RitchRivia
*/
document.addEventListener("DOMContentLoaded", function() {
    // Accroches saisies dans l'admin, transmises par la page en JSON
    const textArray = JSON.parse(document.getElementById('taglines').textContent);
    const typingSpeed = 100;
    const erasingSpeed = 50;
    const initialDelay = 200;
    const newTextDelay = 2000;

    let textArrayIndex = 0;
    let charIndex = 0;
    const typewriterSpan = document.getElementById('typewriter');

    function type() {
        if (charIndex < textArray[textArrayIndex].length) {
            typewriterSpan.textContent += textArray[textArrayIndex].charAt(charIndex);
            charIndex++;
            setTimeout(type, typingSpeed);
        } else {
            setTimeout(erase, newTextDelay);
        }
    }

    function erase() {
        if (charIndex > 0) {
            typewriterSpan.textContent = textArray[textArrayIndex].substring(0, charIndex - 1);
            charIndex--;
            setTimeout(erase, erasingSpeed);
        } else {
            textArrayIndex++;
            if (textArrayIndex >= textArray.length) textArrayIndex = 0;
            setTimeout(type, typingSpeed + 500);
        }
    }

    typewriterSpan.textContent = '';
    if (textArray.length > 0) setTimeout(type, initialDelay);
});


// Script pour animer les bulles
const canvas = document.getElementById('bubbles-canvas');
const ctx = canvas.getContext('2d');

let width, height;
let bubbles = [];

function init() {
    resizeCanvas();
    createBubbles();
    animate();
    window.addEventListener('resize', resizeCanvas);
}

// Ajuste la taille du canvas
function resizeCanvas() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
}

// Crée des bulles
function createBubbles() {
    bubbles = [];
    const numBubbles = Math.floor(width / 50); // Nombre de bulles basé sur la largeur

    for (let i = 0; i < numBubbles; i++) {
        bubbles.push({
            x: Math.random() * width,
            y: Math.random() * height,
            radius: 5 + Math.random() * 15,
            velocityX: (Math.random() - 0.5) * 0.5,
            velocityY: (Math.random() - 0.5) * 0.5,
            opacity: Math.random() * 0.8 + 0.2
        });
    }
}

// Anime les bulles
function animate() {
    ctx.clearRect(0, 0, width, height);

    for (const bubble of bubbles) {
        // Déplacement
        bubble.x += bubble.velocityX;
        bubble.y += bubble.velocityY;

        // Rebond sur les bords
        if (bubble.x < 0 || bubble.x > width) bubble.velocityX *= -1;
        if (bubble.y < 0 || bubble.y > height) bubble.velocityY *= -1;

        // Dessine la bulle
        ctx.beginPath();
        ctx.arc(bubble.x, bubble.y, bubble.radius, 0, 2 * Math.PI, false);
        ctx.fillStyle = `rgba(255, 255, 255, ${bubble.opacity})`;
        ctx.fill();
    }

    requestAnimationFrame(animate);
}

init();





// Affiche la description comme du texte. Seule exception : un lien <a href="http(s)://...">
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

// Affiche une date de la modale, ou masque la ligne si elle est absente
function setModalDate(elementId, value) {
    const line = document.getElementById(elementId);
    line.querySelector('span').textContent = value || '';
    line.style.display = value ? 'block' : 'none';
}

function openModal(button) {
    // Les attributs data-* sont lus comme du texte, jamais interprétés comme du HTML.
    // Les retours à la ligne de la description sont rendus par le CSS (white-space: pre-line).
    document.getElementById('modalTitle').textContent = button.getAttribute('data-title');
    renderDescription(document.getElementById('modalDescription'), button.getAttribute('data-description') || '');
    setModalDate('modalStartDate', button.getAttribute('data-start-date'));
    setModalDate('modalEndDate', button.getAttribute('data-end-date'));

    // Afficher la modale
    document.getElementById('projectModal').style.display = 'flex';
}


function closeModal() {
    // Masquer la modale
    document.getElementById('projectModal').style.display = 'none';
}

document.querySelectorAll('.project-button, .experience-button').forEach((button) => {
    button.addEventListener('click', () => openModal(button));
});
document.getElementById('modalClose').addEventListener('click', closeModal);

// Fermer la modale si l'utilisateur clique en dehors du contenu de la modale
window.onclick = function(event) {
    var modal = document.getElementById("projectModal");
    if (event.target === modal) {
        closeModal();
    }
}


document.addEventListener("DOMContentLoaded", () => {
    const containers = document.querySelectorAll('.container'); // tous les containers de la timeline

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                // Ajoute un délai progressif basé sur l'index pour éviter l'affichage simultané
                const delay = Array.from(containers).indexOf(entry.target) * 200; // 200ms par conteneur
                setTimeout(() => {
                    entry.target.classList.add('show');
                }, delay);

                observer.unobserve(entry.target); // Arrête d'observer cet élément
            }
        });
    }, {
        threshold: 0.1 // Déclenche lorsque 10% de l'élément est visible
    });

    containers.forEach(container => {
        observer.observe(container);
    });
});


function toggleMenu() {
    const navbar = document.getElementById('myNavbar');
    if (navbar.classList.contains('collapsed')) {
        navbar.classList.remove('collapsed');
        navbar.classList.add('expanded');
    } else {
        navbar.classList.remove('expanded');
        navbar.classList.add('collapsed');
    }
}

document.getElementById('burger-menu').addEventListener('click', toggleMenu);

// Désactiver/activer le bouton en fonction de la case
const checkbox = document.getElementById('consent');
const submitButton = document.getElementById('submit-button');
checkbox.addEventListener('change', () => {
    submitButton.disabled = !checkbox.checked;
});
