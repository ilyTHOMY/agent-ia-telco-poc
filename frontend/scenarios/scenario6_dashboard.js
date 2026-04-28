/**
 * Scenario 6 — Dashboard operateur, metriques temps reel
 * Pas de client — vue operateur uniquement
 */
const SCENARIO_6 = {
  id: "S6",
  titre: "Dashboard operateur — Metriques temps reel",
  canal: "dashboard",
  url: "/pages/dashboard.html",
  points_demo: [
    "KPIs en temps reel : tickets total, ouverts, P1, taux resolution, sessions actives",
    "Tableau tickets avec filtres statut/priorite et telechargement PDF",
    "Graphiques repartition par type (fraude, transaction, agent...) et par canal",
    "Donut chart resolution autonome vs escalade",
    "Auto-refresh toutes les 5 secondes — simulate activite en direct",
    "Lancer les scenarios S1 a S5 en parallele pour voir le dashboard se peupler",
  ],
  description: "Vue operateur complete avec metriques temps reel. Lancer les autres scenarios en parallele pour voir les tickets apparaitre en live.",
};

// Genere des tickets fictifs pour la demo si la BDD est vide
async function peupler_dashboard_demo() {
  const API = "http://localhost:8000/api/v1";
  const ticketsDemo = [
    { telephone: "+221771234567", type: "transaction_non_recue", priorite: "P2", canal: "chat" },
    { telephone: "+221783456789", type: "depot_non_credite", priorite: "P2", canal: "chat" },
    { telephone: "+221774567890", type: "fraude_sim_swap", priorite: "P1", canal: "whatsapp" },
    { telephone: "+221784567890", type: "retrait_echoue", priorite: "P3", canal: "ussd" },
  ];
  for (const t of ticketsDemo) {
    try {
      await fetch(`${API}/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id_session: "demo_" + Date.now() + Math.random(),
          telephone: t.telephone,
          message: "demo scenario " + t.type,
          canal: t.canal,
        }),
      });
      await new Promise(r => setTimeout(r, 300));
    } catch(e) {}
  }
  console.log("[S6] Dashboard peuple avec donnees de demo");
}

if (typeof module !== "undefined") module.exports = { SCENARIO_6, peupler_dashboard_demo };
