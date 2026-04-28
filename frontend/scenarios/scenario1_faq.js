/**
 * Scenario 1 — FAQ & Self-service multilingue
 * Client : Moussa Diallo (Wave, FR → WO)
 * Telephone : +221771234567 | PIN : 1234
 */
const SCENARIO_1 = {
  id: "S1",
  titre: "FAQ & Self-service multilingue",
  telephone: "+221771234567",
  pin: "1234",
  operateur: "wave",
  langue_debut: "fr",
  etapes: [
    { role: "client", message: "1234", note: "Authentification PIN" },
    { role: "attente", ms: 800 },
    { role: "client", message: "Bonjour, quels sont les frais de transfert Wave ?", note: "FAQ frais" },
    { role: "attente", ms: 1200 },
    { role: "client", message: "Et ma limite journaliere de transaction ?", note: "FAQ limites" },
    { role: "attente", ms: 1000 },
    { role: "client", message: "sama solde bi ?", note: "Passage en wolof - consultation solde" },
    { role: "attente", ms: 900 },
    { role: "client", message: "jere jef", note: "Remerciement en wolof" },
  ],
  description: "Ce scenario illustre la FAQ self-service avec bascule automatique de langue francais vers wolof. L'agent IA detecte le changement de langue et adapte sa reponse.",
};

async function lancerScenario1(wsRef, delaiBase = 1500) {
  if (!wsRef || wsRef.readyState !== WebSocket.OPEN) {
    console.warn("[S1] WebSocket non disponible");
    return;
  }
  for (const etape of SCENARIO_1.etapes) {
    if (etape.role === "attente") {
      await new Promise(r => setTimeout(r, etape.ms));
    } else if (etape.role === "client") {
      await new Promise(r => setTimeout(r, delaiBase));
      wsRef.send(JSON.stringify({ message: etape.message }));
      console.log(`[S1] Envoi : "${etape.message}" (${etape.note})`);
    }
  }
}

if (typeof module !== "undefined") module.exports = { SCENARIO_1, lancerScenario1 };
