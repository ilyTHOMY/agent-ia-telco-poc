/**
 * rapport.js — telechargement et affichage des rapports PDF/JSON
 * Utilise par le chat et le dashboard
 */
const Rapport = {

  async telechargerPDF(idTicket) {
    const url = `http://localhost:8000/api/v1/rapports/${idTicket}/pdf`;
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `rapport-${idTicket}.pdf`;
      a.click();
      URL.revokeObjectURL(a.href);
      return true;
    } catch(e) {
      console.error("[RAPPORT] Erreur telechargement PDF :", e);
      return false;
    }
  },

  async obtenirJSON(idTicket) {
    const url = `http://localhost:8000/api/v1/rapports/${idTicket}/json`;
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch(e) {
      console.error("[RAPPORT] Erreur JSON :", e);
      return null;
    }
  },

  afficherDansPanneau(idTicket, conteneur) {
    if (!conteneur) return;
    conteneur.innerHTML = `
      <div style="padding:.5rem;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;font-size:.78rem">
        <div style="font-weight:600;margin-bottom:.4rem">Ticket ${idTicket}</div>
        <a href="http://localhost:8000/api/v1/rapports/${idTicket}/pdf" target="_blank"
           style="color:#1D4ED8;text-decoration:none">
          ↓ Telecharger rapport PDF
        </a>
        &nbsp;|&nbsp;
        <a href="http://localhost:8000/api/v1/rapports/${idTicket}/json" target="_blank"
           style="color:#0D9488;text-decoration:none">
          { } Voir JSON
        </a>
      </div>`;
  }
};

if (typeof module !== "undefined") module.exports = Rapport;
