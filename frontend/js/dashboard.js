const API = "http://localhost:8000/api/v1";
let tousLesTickets = [];

async function chargerMetriques() {
  try {
    const res = await fetch(`${API}/dashboard/metriques`);
    const data = await res.json();

    // KPIs
    document.getElementById("kpi-total").textContent = data.kpis.total_tickets;
    document.getElementById("kpi-ouverts").textContent = data.kpis.tickets_ouverts;
    document.getElementById("kpi-resolus").textContent = data.kpis.tickets_resolus;
    document.getElementById("kpi-p1").textContent = data.kpis.incidents_p1;
    document.getElementById("kpi-taux").textContent = data.kpis.taux_resolution_pct + "%";
    document.getElementById("kpi-sessions").textContent = data.kpis.sessions_actives;

    // Tickets
    tousLesTickets = data.tickets_recents || [];
    afficherTickets(tousLesTickets);

    // Graphiques
    afficherGraphique("chart-types", data.repartition_types || {});
    afficherGraphique("chart-canaux", data.repartition_canaux || {}, "#0D9488");

  } catch(e) {
    console.warn("API non disponible :", e.message);
    document.getElementById("kpi-total").textContent = "—";
  }
}

function afficherTickets(tickets) {
  const tbody = document.getElementById("tickets-tbody");
  if (!tickets.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty-state">Aucun ticket pour le moment.</td></tr>';
    return;
  }
  tbody.innerHTML = tickets.map(t => {
    const date = t.date_ouverture ? t.date_ouverture.slice(0,16).replace("T"," ") : "—";
    const prioriteBadge = `<span class="badge-${t.priorite.toLowerCase()}">${t.priorite}</span>`;
    const statutBadge = `<span class="badge-${t.statut}">${t.statut.replace("_"," ")}</span>`;
    return `<tr>
      <td style="font-family:monospace;font-size:0.78rem">${t.id}</td>
      <td>${(t.type_reclamation||"—").replace(/_/g," ")}</td>
      <td>${t.canal_origine||"—"}</td>
      <td>${prioriteBadge}</td>
      <td>${statutBadge}</td>
      <td>${date}</td>
      <td>${t.sla_heures}h</td>
      <td><a class="btn-pdf" href="${API}/rapports/${t.id}/pdf" target="_blank">PDF</a></td>
    </tr>`;
  }).join("");
}

function filtrerTickets() {
  const statut = document.getElementById("filtre-statut").value;
  const priorite = document.getElementById("filtre-priorite").value;
  let filtres = tousLesTickets;
  if (statut) filtres = filtres.filter(t => t.statut === statut);
  if (priorite) filtres = filtres.filter(t => t.priorite === priorite);
  afficherTickets(filtres);
}

function afficherGraphique(id, data, couleur = "#1D4ED8") {
  const zone = document.getElementById(id);
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
  const trie = Object.entries(data).sort((a, b) => b[1] - a[1]);

  zone.innerHTML = trie.map(([label, count]) => {
    const pct = Math.round((count / total) * 100);
    return `<div class="chart-bar-row">
      <div class="chart-bar-label">${label.replace(/_/g," ")}</div>
      <div class="chart-bar-track">
        <div class="chart-bar-fill" style="width:${pct}%;background:${couleur}"></div>
      </div>
      <div class="chart-bar-count">${count}</div>
    </div>`;
  }).join("") || '<div class="empty-state">Aucune donnee</div>';
}

// Chargement initial + polling 5s
chargerMetriques();
setInterval(chargerMetriques, 5000);