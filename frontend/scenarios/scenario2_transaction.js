/**
 * Scenario 2 — Transaction echouee, resolution autonome
 * Client : Aminata Cisse (Orange Money, FR)
 * Telephone : +221781234567 | PIN : 9999
 */
const SCENARIO_2 = {
  id: "S2",
  titre: "Transaction echouee — Resolution autonome",
  telephone: "+221781234567",
  pin: "9999",
  operateur: "orange_money",
  etapes: [
    { role: "client", message: "9999", note: "Auth PIN" },
    { role: "attente", ms: 800 },
    { role: "client", message: "Bonjour j'ai envoye 25000 XOF il y a 2 heures mais le beneficiaire n'a pas recu", note: "Signalement transaction" },
    { role: "attente", ms: 1500 },
    { role: "client", message: "La reference c'est OM-20260326-5521", note: "Fourniture reference" },
    { role: "attente", ms: 1200 },
    { role: "client", message: "Est ce que je peux avoir un remboursement si ca n'arrive pas ?", note: "Question remboursement" },
    { role: "attente", ms: 1000 },
    { role: "client", message: "Merci pour votre aide", note: "Fin resolution autonome" },
  ],
  description: "L'IA retrouve la transaction via la reference, diagnostique le statut et informe le client. Resolution complete sans escalade.",
};

async function lancerScenario2(wsRef, delaiBase = 1500) {
  if (!wsRef || wsRef.readyState !== WebSocket.OPEN) return;
  for (const etape of SCENARIO_2.etapes) {
    if (etape.role === "attente") {
      await new Promise(r => setTimeout(r, etape.ms));
    } else if (etape.role === "client") {
      await new Promise(r => setTimeout(r, delaiBase));
      wsRef.send(JSON.stringify({ message: etape.message }));
    }
  }
}

if (typeof module !== "undefined") module.exports = { SCENARIO_2, lancerScenario2 };
