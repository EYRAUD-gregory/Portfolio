// Chargé dans l'en-tête, avant le premier affichage : la page ne s'allume pas en clair
// pour basculer ensuite en sombre. Thème retenu par le visiteur, sinon celui de son système.
(function () {
  var root = document.documentElement, saved = null;
  try { saved = localStorage.getItem('theme'); } catch (error) {}
  if (saved !== 'dark' && saved !== 'light') {
    saved = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  root.dataset.theme = saved;
  // Les apparitions au défilement ne masquent les blocs que si le script est là pour les révéler
  root.classList.add('js');
})();
