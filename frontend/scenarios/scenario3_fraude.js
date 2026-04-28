/**
 * Scenario 3 — Escalade fraude / SIM swap detecte
 * Client : Mamadou Ba (Wave, FR-WO)
 * Telephone : +221774567890 | PIN : 1111
 */
const SCENARIO_3 = {
  id: "S3",
  titre: "Escalade fraude — SIM swap detecte",
  telephone: "+221774567890",
  pin: "1111",
  operateur: "wave",
  etapes: [
    { role: "client", message: "1111", note: "Auth PIN" },
    { role: "attente", ms: 800 },
    { role: "client", message: "Mon compte a fait des transactions que je n'ai absolument pas faites ! Quelqu'un utilise mon compte sans mon accord !", note: "Signalement fraude - escalade P1 attendue" },
    { role: "attente", ms: 2000 },
    { role: "client", message: "C'est une arnaque je pense que j'ai eu un SIM swap", note: "Confirmation fraude" },
    { role: "attente", ms: 1500 },
    { role: "client", message: "Bloquez mon compte immediatement s'il vous plait", note: "Demande blocage urgent" },
  ],
  description: "Detecte les signaux de fraude et de SIM swap. Declenche escalade P1 vers equipe securite, bloque le compte, cree ticket urgent SLA < 5 min.",
  escalade_attendue: { regle: "fraude_sim_swap", priorite: "P1", sla: "5 min" },
};

async function lancerScenario3(wsRef, delaiBase = 1800) {
  if (!wsRef || wsRef.readyState !== WebSocket.OPEN) return;
  for (const etape of SCENARIO_3.etapes) {
    if (etape.role === "attente") {
      await new Promise(r => setTimeout(r, etape.ms));
    } else if (etape.role === "client") {
      await new Promise(r => setTimeout(r, delaiBase));
      wsRef.send(JSON.stringify({ message: etape.message }));
    }
  }
}

if (typeof module !== "undefined") module.exports = { SCENARIO_3, lancerScenario3 };
