/**
 * csat_widget.js — Widget de notation CSAT avec etoiles animees
 * Affiche apres resolution d'une conversation ou fermeture de ticket.
 * Envoie la note a POST /api/v1/dashboard/csat/{id_ticket}
 */

const API = 'http://localhost:8000/api/v1';

const CSAT_STYLE = `
  .csat-overlay {
    position: fixed; inset: 0;
    background: rgba(0,0,0,0.65);
    backdrop-filter: blur(6px);
    z-index: 1000;
    display: flex; align-items: center; justify-content: center;
    animation: csatFadeIn .3s ease;
  }
  @keyframes csatFadeIn { from{opacity:0} to{opacity:1} }

  .csat-card {
    background: #141828;
    border: 1px solid rgba(255,255,255,.12);
    border-radius: 20px;
    padding: 2rem 2.2rem;
    max-width: 380px; width: 90%;
    text-align: center;
    animation: csatSlideUp .35s cubic-bezier(.34,1.56,.64,1);
    box-shadow: 0 24px 64px rgba(0,0,0,.5);
  }
  @keyframes csatSlideUp {
    from{opacity:0;transform:translateY(30px) scale(.94)}
    to{opacity:1;transform:translateY(0) scale(1)}
  }

  .csat-icon {
    width: 56px; height: 56px; border-radius: 50%;
    background: linear-gradient(135deg,#4F6EFF,#00D4B4);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.5rem; margin: 0 auto 1rem;
    box-shadow: 0 8px 24px rgba(79,110,255,.3);
  }

  .csat-title {
    font-size: 1.05rem; font-weight: 700;
    color: #E8ECFF; margin-bottom: .4rem;
    font-family: 'Outfit', sans-serif;
  }
  .csat-sub {
    font-size: .82rem; color: #8B92B8; margin-bottom: 1.4rem;
    font-family: 'Outfit', sans-serif; line-height: 1.5;
  }

  .csat-stars {
    display: flex; justify-content: center; gap: .4rem; margin-bottom: 1.2rem;
  }
  .csat-star {
    font-size: 2rem; cursor: pointer;
    transition: transform .2s cubic-bezier(.34,1.56,.64,1), filter .2s;
    filter: grayscale(1) brightness(.5);
    user-select: none;
  }
  .csat-star:hover { transform: scale(1.25); }
  .csat-star.active {
    filter: grayscale(0) brightness(1);
    animation: starPop .25s cubic-bezier(.34,1.56,.64,1);
  }
  @keyframes starPop {
    0%{transform:scale(1)} 50%{transform:scale(1.4)} 100%{transform:scale(1)}
  }

  .csat-labels {
    display: flex; justify-content: space-between;
    font-size: .68rem; color: #555F85; margin-bottom: 1.2rem;
    padding: 0 .2rem;
  }

  .csat-comment {
    width: 100%;
    background: #1C2235; border: 1px solid rgba(255,255,255,.08);
    border-radius: 10px; padding: .55rem .8rem;
    color: #E8ECFF; font-size: .82rem;
    font-family: 'Outfit', sans-serif;
    resize: none; outline: none;
    margin-bottom: 1rem;
    transition: border-color .2s;
  }
  .csat-comment:focus { border-color: #4F6EFF; }
  .csat-comment::placeholder { color: #555F85; }

  .csat-btns { display: flex; gap: .6rem; }

  .csat-btn-submit {
    flex: 1; padding: .6rem;
    background: linear-gradient(135deg,#4F6EFF,#6B86FF);
    border: none; border-radius: 10px;
    color: white; font-size: .88rem; font-weight: 700;
    font-family: 'Outfit', sans-serif; cursor: pointer;
    transition: all .15s;
    box-shadow: 0 4px 16px rgba(79,110,255,.3);
  }
  .csat-btn-submit:hover { transform: translateY(-1px); }
  .csat-btn-submit:disabled { opacity: .5; cursor: not-allowed; transform: none; }

  .csat-btn-skip {
    padding: .6rem .9rem;
    background: transparent; border: 1px solid rgba(255,255,255,.1);
    border-radius: 10px; color: #8B92B8;
    font-size: .82rem; font-family: 'Outfit', sans-serif; cursor: pointer;
    transition: all .15s;
  }
  .csat-btn-skip:hover { border-color: rgba(255,255,255,.2); color: #E8ECFF; }

  .csat-success {
    animation: csatSuccess .4s ease;
  }
  @keyframes csatSuccess {
    0%{transform:scale(1)} 50%{transform:scale(1.05)} 100%{transform:scale(1)}
  }
`;

function _injecterStyles() {
  if (document.getElementById('csat-styles')) return;
  const style = document.createElement('style');
  style.id = 'csat-styles';
  style.textContent = CSAT_STYLE;
  document.head.appendChild(style);
}

const LABELS = ['Tres insatisfait', 'Insatisfait', 'Neutre', 'Satisfait', 'Tres satisfait'];
const EMOJIS_ETOILE = ['⭐', '⭐', '⭐', '⭐', '⭐'];

/**
 * Affiche le widget CSAT.
 * @param {string} idTicket - ID du ticket a noter
 * @param {function} onClose - Callback apres fermeture
 */
function afficherCSAT(idTicket, onClose = null) {
  _injecterStyles();

  let noteSelectionnee = 0;

  const overlay = document.createElement('div');
  overlay.className = 'csat-overlay';
  overlay.id = 'csat-overlay';

  overlay.innerHTML = `
    <div class="csat-card" id="csat-card">
      <div class="csat-icon">⭐</div>
      <div class="csat-title">Comment s'est passee cette interaction ?</div>
      <div class="csat-sub">Votre avis nous aide a ameliorer le service.<br>Ticket : <span style="font-family:monospace;color:#4F6EFF;font-size:.78rem">${idTicket}</span></div>
      <div class="csat-stars" id="csat-stars">
        ${[1,2,3,4,5].map(i => `<span class="csat-star" data-note="${i}" title="${LABELS[i-1]}">⭐</span>`).join('')}
      </div>
      <div class="csat-labels">
        <span>😞 Mauvais</span>
        <span>😊 Excellent</span>
      </div>
      <textarea class="csat-comment" id="csat-comment" rows="2"
        placeholder="Un commentaire ? (optionnel)"></textarea>
      <div class="csat-btns">
        <button class="csat-btn-skip" onclick="fermerCSAT()">Passer</button>
        <button class="csat-btn-submit" id="csat-submit" disabled onclick="soumettreCSAT('${idTicket}')">
          Envoyer →
        </button>
      </div>
    </div>`;

  document.body.appendChild(overlay);

  // Etoiles interactives
  const etoiles = overlay.querySelectorAll('.csat-star');
  etoiles.forEach(etoile => {
    etoile.addEventListener('mouseover', () => {
      const note = parseInt(etoile.dataset.note);
      etoiles.forEach((e, i) => {
        e.style.filter = i < note ? 'grayscale(0) brightness(1)' : 'grayscale(1) brightness(.5)';
        e.style.transform = i < note ? 'scale(1.1)' : 'scale(1)';
      });
    });

    etoile.addEventListener('mouseout', () => {
      etoiles.forEach((e, i) => {
        const actif = i < noteSelectionnee;
        e.style.filter = actif ? 'grayscale(0) brightness(1)' : 'grayscale(1) brightness(.5)';
        e.style.transform = 'scale(1)';
        e.classList.toggle('active', actif);
      });
    });

    etoile.addEventListener('click', () => {
      noteSelectionnee = parseInt(etoile.dataset.note);
      etoiles.forEach((e, i) => {
        const actif = i < noteSelectionnee;
        e.classList.toggle('active', actif);
        e.style.filter = actif ? 'grayscale(0) brightness(1)' : 'grayscale(1) brightness(.5)';
      });
      document.getElementById('csat-submit').disabled = false;

      // Animation de la carte
      const card = document.getElementById('csat-card');
      card.style.animation = 'none';
      card.offsetHeight;
      card.classList.add('csat-success');
    });
  });

  window._csatOnClose = onClose;
  window._csatNote = () => noteSelectionnee;
}

async function soumettreCSAT(idTicket) {
  const note = window._csatNote?.() || 0;
  if (!note) return;

  const commentaire = document.getElementById('csat-comment')?.value || '';
  const btn = document.getElementById('csat-submit');
  btn.disabled = true;
  btn.textContent = 'Envoi...';

  try {
    await fetch(`${API}/dashboard/csat/${idTicket}?note=${note}&commentaire=${encodeURIComponent(commentaire)}`, {
      method: 'POST',
    });
  } catch(e) {
    console.warn('[CSAT] Erreur envoi :', e.message);
  }

  // Animation succes
  const card = document.getElementById('csat-card');
  card.innerHTML = `
    <div style="padding:1rem 0">
      <div style="font-size:3rem;margin-bottom:.8rem;animation:starPop .4s ease">⭐</div>
      <div style="font-size:1.1rem;font-weight:700;color:#E8ECFF;margin-bottom:.4rem">Merci pour votre avis !</div>
      <div style="font-size:.82rem;color:#8B92B8">Votre note : ${'⭐'.repeat(note)}</div>
    </div>`;

  setTimeout(() => fermerCSAT(), 1800);
}

function fermerCSAT() {
  const overlay = document.getElementById('csat-overlay');
  if (overlay) {
    overlay.style.animation = 'csatFadeIn .2s ease reverse forwards';
    setTimeout(() => {
      overlay.remove();
      if (window._csatOnClose) window._csatOnClose();
    }, 200);
  }
}

/**
 * Declenche automatiquement le CSAT apres un delai.
 * @param {string} idTicket
 * @param {number} delaiMs - Delai en ms avant affichage (defaut 2s)
 */
function declencherCSATAuto(idTicket, delaiMs = 2000) {
  if (!idTicket) return;
  setTimeout(() => afficherCSAT(idTicket), delaiMs);
}

if (typeof module !== 'undefined') module.exports = { afficherCSAT, fermerCSAT, declencherCSATAuto };
