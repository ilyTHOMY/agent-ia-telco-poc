/**
 * theme_toggle.js — Switch theme clair/sombre avec animation fondu
 * Inclure dans toutes les pages HTML avant </body>
 * Le bouton doit avoir id="theme-btn"
 */

const THEME_KEY = 'agentia_theme';

const THEMES = {
  dark: {
    '--bg':      '#0C0F1A',
    '--bg2':     '#141828',
    '--bg3':     '#1C2235',
    '--surface': '#232840',
    '--border':  'rgba(255,255,255,0.07)',
    '--border2': 'rgba(255,255,255,0.13)',
    '--text':    '#E8ECFF',
    '--text2':   '#8B92B8',
    '--text3':   '#555F85',
  },
  light: {
    '--bg':      '#9AAEF5',
    '--bg2':     '#A8BAFF',
    '--bg3':     '#C2CEFF',
    '--surface': '#8EA0E8',
    '--border':  'rgba(20,30,80,0.12)',
    '--border2': 'rgba(20,30,80,0.22)',
    '--text':    '#0C0F1A',
    '--text2':   '#1E2D6B',
    '--text3':   '#3A4A90',
  }
};

function appliquerTheme(theme, animate = false) {
  const root = document.documentElement;
  const vars = THEMES[theme];

  if (animate) {
    // Overlay de fondu
    const overlay = document.createElement('div');
    overlay.style.cssText = `
      position: fixed; inset: 0; z-index: 9999;
      background: ${theme === 'light' ? '#fff' : '#0C0F1A'};
      opacity: 0; pointer-events: none;
      transition: opacity 0.25s ease;
    `;
    document.body.appendChild(overlay);

    // Fondu entrant
    requestAnimationFrame(() => {
      overlay.style.opacity = '0.85';
      setTimeout(() => {
        // Appliquer les variables
        Object.entries(vars).forEach(([k, v]) => root.style.setProperty(k, v));
        root.setAttribute('data-theme', theme);
        // Fondu sortant
        overlay.style.opacity = '0';
        setTimeout(() => overlay.remove(), 280);
      }, 250);
    });
  } else {
    Object.entries(vars).forEach(([k, v]) => root.style.setProperty(k, v));
    root.setAttribute('data-theme', theme);
  }

  localStorage.setItem(THEME_KEY, theme);
  majBouton(theme);
}

function majBouton(theme) {
  const btn = document.getElementById('theme-btn');
  if (!btn) return;
  const isLight = theme === 'light';
  btn.innerHTML = isLight
    ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
       </svg>`
    : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="5"/>
        <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
        <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
       </svg>`;
  btn.title = isLight ? 'Passer en mode sombre' : 'Passer en mode clair';
}

function toggleTheme() {
  const actuel = localStorage.getItem(THEME_KEY) || 'dark';
  const nouveau = actuel === 'dark' ? 'light' : 'dark';

  // Animation du bouton
  const btn = document.getElementById('theme-btn');
  if (btn) {
    btn.style.transform = 'scale(0.8) rotate(180deg)';
    btn.style.transition = 'transform 0.3s cubic-bezier(0.34,1.56,0.64,1)';
    setTimeout(() => {
      btn.style.transform = 'scale(1) rotate(0deg)';
    }, 300);
  }

  appliquerTheme(nouveau, true);
}

// Init au chargement
(function init() {
  const theme = localStorage.getItem(THEME_KEY) || 'dark';
  appliquerTheme(theme, false);

  // Creer le bouton si pas encore dans le DOM
  // (sinon appeler manuellement depuis le HTML)
  document.addEventListener('DOMContentLoaded', () => {
    majBouton(theme);
  });
})();
