document.addEventListener("DOMContentLoaded", function() {
    const textArray = ["Ingénieur IA", "Ingénieur Data", "Développeur Python"];
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
