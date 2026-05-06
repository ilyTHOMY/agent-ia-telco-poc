/**
 * ussd.js — Logique du simulateur USSD
 * Utilisé par ussd_v2.html
 */

const API = 'http://localhost:8000/api/v1';
let sessionId = null, navigation = '', actif = false;

function genSessId() {
  return 'ussd_' + Date.now() + '_' + Math.random().toString(36).slice(2, 6);
}

function heure() {
  return new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function ecrireEcran(texte) {
  const screen = document.getElementById('screen');
  if (!screen) return;
  const propre = texte.replace(/^(CON|END)\s?/, '');
  screen.innerHTML = propre + '\n<div class="cursor-line">› <div class="cursor-blink"></div></div>';
  screen.scrollTop = screen.scrollHeight;
}

function log(texte, type = 'sys') {
  const zone = document.getElementById('log-lines');
  if (!zone) return;
  const div = document.createElement('div');
  div.className = 'log-line log-' + type;
  div.textContent = `[${heure()}] ${texte}`;
  zone.appendChild(div);
  zone.scrollTop = zone.scrollHeight;
}

function viderLog() {
  const zone = document.getElementById('log-lines');
  if (zone) zone.innerHTML = '';
}

function taper(c) {
  if (!actif) return;
  const saisieEl = document.getElementById('saisie-path');
  const current = saisieEl ? saisieEl.textContent.replace('—', '') : '';
  const nouvelle = current === '—' ? c : current + c;
  if (saisieEl) saisieEl.textContent = nouvelle || '—';
}

function effacer() {
  const saisieEl = document.getElementById('saisie-path');
  if (!saisieEl) return;
  const current = saisieEl.textContent;
  if (current && current !== '—') {
    saisieEl.textContent = current.slice(0, -1) || '—';
  }
}

async function confirmer() {
  if (!actif) return;
  const saisieEl = document.getElementById('saisie-path');
  const saisie = saisieEl ? saisieEl.textContent.replace('—', '') : '';
  if (!saisie) return;

  navigation = navigation ? navigation + '*' + saisie : saisie;
  log('Saisie : ' + saisie + ' → navigation : ' + navigation, 'out');

  const navEl = document.getElementById('nav-path');
  if (navEl) navEl.textContent = navigation;
  if (saisieEl) saisieEl.textContent = '—';

  await envoyerUSSD(navigation);
}

async function demarrer() {
  sessionId = genSessId();
  navigation = '';
  actif = true;
  viderLog();

  const navEl = document.getElementById('nav-path');
  const saisieEl = document.getElementById('saisie-path');
  const badgeEl = document.getElementById('nav-badge');

  if (navEl) navEl.textContent = '—';
  if (saisieEl) saisieEl.textContent = '—';
  if (badgeEl) {
    badgeEl.textContent = 'Actif';
    badgeEl.style.background = 'rgba(0,217,126,.12)';
    badgeEl.style.color = 'var(--green, #00D97E)';
  }

  log('SESSION DEMARREE : ' + sessionId, 'sys');
  ecrireEcran('Connexion en cours...');
  await envoyerUSSD('');
}

async function envoyerUSSD(texte) {
  const telephone = document.getElementById('ussd-tel')?.value || '+221781234567';
  const code = document.getElementById('ussd-code')?.value || '*144#';

  try {
    const res = await fetch(`${API}/canaux/ussd`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sessionId,
        phoneNumber: telephone,
        text: texte,
        serviceCode: code,
      }),
    });

    const reponse = await res.text();
    log('Reponse : ' + reponse.slice(0, 80), 'in');
    ecrireEcran(reponse);

    if (reponse.startsWith('END')) {
      actif = false;
      const badgeEl = document.getElementById('nav-badge');
      if (badgeEl) {
        badgeEl.textContent = 'Termine';
        badgeEl.style.background = 'rgba(139,146,184,.1)';
        badgeEl.style.color = 'var(--text3, #555F85)';
      }
      log('SESSION TERMINEE', 'sys');
    }
  } catch (e) {
    ecrireEcran('Erreur : API non disponible.\nVerifiez que le backend tourne sur localhost:8000');
    log('ERREUR : ' + e.message, 'err');
    actif = false;
  }
}

async function reinitialiser() {
  actif = false;
  navigation = '';
  sessionId = null;

  const badgeEl = document.getElementById('nav-badge');
  const navEl = document.getElementById('nav-path');
  const saisieEl = document.getElementById('saisie-path');

  if (badgeEl) { badgeEl.textContent = 'Inactif'; badgeEl.style.background = ''; badgeEl.style.color = ''; }
  if (navEl) navEl.textContent = '—';
  if (saisieEl) saisieEl.textContent = '—';

  ecrireEcran('Composez *144# ou *150# puis\nappuyez sur Appeler');
  log('SESSION REINITALISEE', 'sys');
}

async function playScenario(steps) {
  await reinitialiser();
  await new Promise(r => setTimeout(r, 300));
  await demarrer();

  for (let i = 1; i < steps.length; i++) {
    await new Promise(r => setTimeout(r, 1200));
    if (!actif) break;
    navigation = steps.slice(1, i + 1).join('*');
    const navEl = document.getElementById('nav-path');
    if (navEl) navEl.textContent = navigation;
    log('Auto-nav : ' + steps[i], 'out');
    await envoyerUSSD(navigation);
  }
}

function majOperateur() {
  const code = document.getElementById('ussd-code')?.value || '';
  const avatarEl = document.getElementById('ph-avatar');
  const nameEl = document.getElementById('ph-name');
  const opEl = document.getElementById('ph-op');

  if (code.includes('150')) {
    if (avatarEl) avatarEl.textContent = 'MY';
    if (nameEl) nameEl.textContent = 'Mixx by Yas';
    if (opEl) opEl.textContent = 'Service USSD #150#';
  } else {
    if (avatarEl) avatarEl.textContent = 'OM';
    if (nameEl) nameEl.textContent = 'Orange Money';
    if (opEl) opEl.textContent = 'Service USSD #144#';
  }
}

// Heure telephone
function majHeure() {
  const el = document.getElementById('phone-time');
  if (!el) return;
  const now = new Date();
  el.textContent = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
}

// Init
window.addEventListener('load', () => {
  majHeure();
  setInterval(majHeure, 1000);
  demarrer();
});