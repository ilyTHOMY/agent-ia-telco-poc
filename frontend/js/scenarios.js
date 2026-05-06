// Donnees des 6 scenarios
const SCENARIOS = [
  {
    id: "S1",
    titre: "FAQ & Self-service multilingue",
    duree: "8 min",
    desc: "Client Wave consulte les frais et ses limites de transaction, d'abord en francais puis en wolof. L'agent IA adapte sa langue automatiquement.",
    couleur: "#0D9488",
    client: { telephone: "+221771234567", pin: "1234", nom: "Moussa Diallo", langue: "fr" },
    etapes: [
      { role: "client", texte: "Bonjour, quels sont les frais de transfert Wave ?" },
      { role: "ia", texte: "Bonjour Moussa ! Wave applique 1% de frais sur les transferts, avec un plafond a 5 000 FCFA quel que soit le montant. Le depot chez un agent est entierement gratuit." },
      { role: "client", texte: "Et ma limite journaliere ?" },
      { role: "ia", texte: "Votre compte est verifie (KYC complet), donc votre limite journaliere est de 500 000 XOF et mensuelle de 2 000 000 XOF, conformement a la reglementation BCEAO." },
      { role: "client", texte: "sama solde bi ?" },
      { role: "ia", texte: "[Wolof detecte] Sama kalpae bi : 45 200 XOF. Limite journaliere yi : 500 000 XOF." },
    ]
  },
  {
    id: "S2",
    titre: "Transaction echouee — Resolution autonome",
    duree: "10 min",
    desc: "Client Orange Money signale un transfert de 25 000 XOF debite mais non recu. L'IA diagnostique, retrouve la transaction et declenche le remboursement sans intervention humaine.",
    couleur: "#1D4ED8",
    client: { telephone: "+221781234567", pin: "9999", nom: "Aminata Cisse", langue: "fr" },
    etapes: [
      { role: "client", texte: "j'ai envoye 25000 XOF il y a 2 heures mais mon ami n'a pas recu" },
      { role: "ia", texte: "Je comprends votre inquietude Aminata. Pouvez-vous me donner la reference de la transaction ? Elle est visible dans votre historique Orange Money au format OM-AAAAMMJJ-XXXX." },
      { role: "client", texte: "reference OM-20260326-5521" },
      { role: "systeme", texte: "[Systeme] Recherche transaction OM-20260326-5521 → statut : complete, beneficiaire credite" },
      { role: "ia", texte: "J'ai retrouve votre transaction. Elle a bien ete completee et le beneficiaire a ete credite. Votre ami doit verifier son historique Orange Money. Si le probleme persiste apres 30 minutes, recontactez-nous avec cette reference." },
      { role: "client", texte: "ah merci c'etait juste un delai !" },
      { role: "systeme", texte: "[Systeme] Ticket non cree — resolution autonome. CSAT envoye." },
    ]
  },
  {
    id: "S3",
    titre: "Escalade fraude — SIM swap detecte",
    duree: "8 min",
    desc: "Client Wave signale des transactions inconnues sur son compte. L'IA detecte les flags de fraude et de SIM swap dans les donnees transactionnelles et declenche une escalade P1 vers l'equipe securite en moins de 5 minutes.",
    couleur: "#DC2626",
    client: { telephone: "+221774567890", pin: "1111", nom: "Mamadou Ba", langue: "fr-wo" },
    etapes: [
      { role: "client", texte: "mon compte a fait des transactions que je n'ai pas faites ! quelqu'un utilise mon compte" },
      { role: "systeme", texte: "[NLU] Sentiment : frustre. Intention : fraude_suspectee. Mots detectes : 'n'ai pas faites', 'quelqu'un utilise'" },
      { role: "systeme", texte: "[Escalade] Regle 1 declenchee : fraude_sim_swap. Priorite P1. SLA < 5 min." },
      { role: "ia", texte: "Mamadou, je comprends l'urgence. Votre demande est transferee immediatement a notre equipe securite. Un conseiller vous contactera dans moins de 5 minutes. Vos fonds sont en securite." },
      { role: "escalade", texte: "[Ticket INC-774-2026-00001 cree — P1 — Equipe Securite — SLA 5 min]" },
      { role: "systeme", texte: "[Notification SMS] Envoyee a +221774567890 : 'Votre demande INC-774-2026-00001 est prise en urgence...'" },
    ]
  },
  {
    id: "S4",
    titre: "Reclamation complexe — Agent frauduleux",
    duree: "10 min",
    desc: "Client Orange Money Thies : l'agent AGT-TBK-0017 a encaisse 100 000 XOF sans crediter le compte. L'IA cree un ticket P2, signale l'agent au responsable reseau et genere un rapport PDF.",
    couleur: "#7C3AED",
    client: { telephone: "+221783456789", pin: "4444", nom: "Rokhaya Fall", langue: "wo" },
    etapes: [
      { role: "client", texte: "agent bi joxoon ma xaalis waaye compte bi soppaliku" },
      { role: "systeme", texte: "[NLU] Langue : wolof. Intention : depot_non_credite." },
      { role: "systeme", texte: "[Escalade] Regle 6 : litige_agent. Priorite P2. SLA 2h." },
      { role: "ia", texte: "[Wolof] Rokhaya, dama ci dee jafe jafe. Dama ci xool probleme bi. Yonni naa signalement ci responsable reseau agents bi." },
      { role: "systeme", texte: "[Ticket INC-783-2026-00002 cree — P2 — Responsable Reseau Agents]" },
      { role: "systeme", texte: "[Agent AGT-TBK-0017 signale — suspension en cours]" },
      { role: "systeme", texte: "[Rapport PDF genere — envoye par email]" },
      { role: "escalade", texte: "[Resolution sous 2h. Remboursement si fraude confirmee.]" },
    ]
  },
  {
    id: "S5",
    titre: "USSD & Wolof — Client rural",
    duree: "8 min",
    desc: "Client sans smartphone dans une zone rurale. Utilise le canal USSD #150# en tapant uniquement des chiffres. L'arbre de navigation USSD lui permet de signaler un retrait echoue.",
    couleur: "#D97706",
    client: { telephone: "+221784567890", pin: null, canal: "ussd" },
    etapes: [
      { role: "client", texte: "Compose *150#" },
      { role: "systeme", texte: "[USSD] Session ouverte. Affichage menu principal." },
      { role: "ia", texte: "CON Bienvenue Agent IA Mobile Money\n1. Consulter mon solde\n2. Signaler une transaction\n3. Mon compte est bloque\n4. Parler a un conseiller\n5. Questions frequentes" },
      { role: "client", texte: "Saisie : 2" },
      { role: "ia", texte: "CON Type de probleme :\n1. Transfert non recu\n2. Retrait echoue\n3. Depot non credite\n4. Double debit\n0. Retour" },
      { role: "client", texte: "Saisie : 2" },
      { role: "ia", texte: "END Votre retrait echoue est signale. Remboursement eligible si debit effectue. Reference : TKT-USSD-001. SMS de confirmation envoye." },
      { role: "systeme", texte: "[Session USSD terminee. SMS envoye au +221784567890]" },
    ]
  },
  {
    id: "S6",
    titre: "Dashboard operateur — Metriques temps reel",
    duree: "6 min",
    desc: "Vue operateur : metriques en temps reel, tickets P1 urgents, repartition par canal et par type, avec telechargement de rapports PDF.",
    couleur: "#059669",
    client: null,
    etapes: [
      { role: "systeme", texte: "Ouverture du dashboard operateur sur http://localhost:3000/pages/dashboard.html" },
      { role: "systeme", texte: "[Dashboard] Chargement des metriques depuis GET /api/v1/dashboard/metriques" },
      { role: "systeme", texte: "[KPIs] Tickets total : N | Ouverts : N | P1 urgents : N | Taux resolution : N%" },
      { role: "systeme", texte: "[Graphiques] Repartition par type (transaction, fraude, agent...) et par canal (chat, USSD, WA)" },
      { role: "systeme", texte: "[Tickets recents] Liste avec filtre statut/priorite — clic PDF => telechargement rapport" },
      { role: "systeme", texte: "[Auto-refresh] Actualisation automatique toutes les 5 secondes" },
    ]
  },
];

// Rendu des cards
function renderScenarios() {
  const grid = document.getElementById("scenarios-grid");
  grid.innerHTML = SCENARIOS.map(sc => `
    <div class="scenario-card">
      <div class="scenario-header">
        <div class="scenario-num" style="background:${sc.couleur}">${sc.id}</div>
        <div class="scenario-title">${sc.titre}</div>
        <div class="scenario-duree">${sc.duree}</div>
      </div>
      <div class="scenario-body">
        <div class="scenario-desc">${sc.desc}</div>
        <div class="scenario-steps">
          ${sc.etapes.slice(0, 3).map(e => `
            <div class="scenario-step">
              <span class="step-role role-${e.role}">${e.role.toUpperCase()}</span>
              <span>${e.texte.slice(0, 80)}${e.texte.length > 80 ? '...' : ''}</span>
            </div>
          `).join("")}
          ${sc.etapes.length > 3 ? `<div style="font-size:0.75rem;color:var(--gris-text);padding:0.3rem 0">+ ${sc.etapes.length - 3} etapes supplémentaires</div>` : ""}
        </div>
        <div class="scenario-footer">
          ${sc.client ? `<button class="btn-lancer btn-voir-chat" onclick="lancerScenario('${sc.id}')">Lancer dans le chat</button>` : `<button class="btn-lancer btn-voir-chat" onclick="ouvrirDashboard()">Ouvrir le dashboard</button>`}
          <button class="btn-lancer btn-voir-log" onclick="voirScript('${sc.id}')">Voir le script</button>
        </div>
      </div>
    </div>
  `).join("");
}

// Actions
function lancerScenario(id) {
  const sc = SCENARIOS.find(s => s.id === id);
  if (!sc || !sc.client) return;
  // Ouvrir le chat avec les parametres du scenario pre-remplis
  const params = new URLSearchParams({
    tel: sc.client.telephone,
    scenario: id,
  });
  window.open(`chat.html?${params}`, "_blank");
}

function ouvrirDashboard() {
  window.open("dashboard.html", "_blank");
}

function voirScript(id) {
  const sc = SCENARIOS.find(s => s.id === id);
  if (!sc) return;

  document.getElementById("modal-title").textContent = `${sc.id} — ${sc.titre}`;
  document.getElementById("modal-log").innerHTML = sc.etapes.map(e => `
    <div class="log-entry log-${e.role}">
      <strong>${e.role.toUpperCase()}</strong> ${e.texte}
    </div>
  `).join("");
  document.getElementById("modal-overlay").classList.add("open");
}

function fermerModal(event) {
  if (!event || event.target === document.getElementById("modal-overlay")) {
    document.getElementById("modal-overlay").classList.remove("open");
  }
}

// Init
renderScenarios();