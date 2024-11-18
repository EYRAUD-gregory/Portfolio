/* Animation de l'écriture des postes
    Ritch Rivia: https://www.youtube.com/watch?v=161yxE3-00o&ab_channel=RitchRivia
*/
document.addEventListener("DOMContentLoaded", function() {
    const textArray = ["Ingénieur IA", "Data Scientist/Engineer/Analyst", "Développeur Python"];
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
    setTimeout(type, initialDelay);
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





function openModal(button) {
    // Récupère les informations du projet à partir des attributs data-*
    var title = button.getAttribute("data-title");
    var description = button.getAttribute("data-description").replace(/\\u000D\\u000A|\\u000D|\\u000A/g, "<br>"); // Remplacer les retours à la ligne par <br>
    var startDate = button.getAttribute("data-start-date");
    var endDate = button.getAttribute("data-end-date");

    // Assigner les données aux éléments de la modale
    document.getElementById("modalTitle").textContent = title;
    document.getElementById("modalDescription").innerHTML = description; // Utilise innerHTML ici pour traiter le texte comme du HTML
    document.getElementById("modalStartDate").innerHTML = "<b>Date de début : </b>" + startDate;
    document.getElementById("modalEndDate").innerHTML = "<b>Date de fin : </b>" + endDate;

    // Afficher la modale
    document.getElementById("projectModal").style.display = "flex";
}


function closeModal() {
    // Masquer la modale
    document.getElementById("projectModal").style.display = "none";
}

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





