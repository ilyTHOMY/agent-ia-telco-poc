/**
 * Scenario 4 — Reclamation complexe, litige agent
 * Client : Rokhaya Fall (Orange Money, WO)
 * Telephone : +221783456789 | PIN : 4444
 */
const SCENARIO_4 = {
  id: "S4",
  titre: "Reclamation complexe — Agent frauduleux",
  telephone: "+221783456789",
  pin: "4444",
  operateur: "orange_money",
  etapes: [
    { role: "client", message: "4444", note: "Auth PIN" },
    { role: "attente", ms: 800 },
    { role: "client", message: "agent bi joxoon ma xaalis waaye compte bi soppaliku", note: "Depot non credite en wolof" },
    { role: "attente", ms: 1500 },
    { role: "client", message: "dax na 100000 XOF ci agent bi ci Thies waaye amul ci sama compte bi", note: "Details en wolof - montant 100k XOF" },
    { role: "attente", ms: 1200 },
    { role: "client", message: "agent bi tudd AGT-TBK-0017 ci Thies", note: "Identification agent frauduleux" },
    { role: "attente", ms: 1000 },
    { role: "client", message: "lutax lena am sama xaalis bi ?", note: "Question remboursement en wolof" },
  ],
  description: "Client en wolof signale un agent frauduleux (AGT-TBK-0017 deja suspendu). L'IA detecte le litige agent, escalade P2 vers responsable reseau, signale l'agent, genere rapport PDF.",
  escalade_attendue: { regle: "litige_agent", priorite: "P2", sla: "2h" },
};

async function lancerScenario4(wsRef, delaiBase = 2000) {
  if (!wsRef || wsRef.readyState !== WebSocket.OPEN) return;
  for (const etape of SCENARIO_4.etapes) {
    if (etape.role === "attente") {
      await new Promise(r => setTimeout(r, etape.ms));
    } else if (etape.role === "client") {
      await new Promise(r => setTimeout(r, delaiBase));
      wsRef.send(JSON.stringify({ message: etape.message }));
    }
  }
}

if (typeof module !== "undefined") module.exports = { SCENARIO_4, lancerScenario4 };
