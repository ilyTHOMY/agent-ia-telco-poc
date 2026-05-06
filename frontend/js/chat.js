// Configuration 
const API_BASE = "http://localhost:8000/api/v1";
const WS_BASE  = "ws://localhost:8000/api/v1";

let ws = null;
let idSession = null;
let telephone = null;
let authenticated = false;
let etapeAuth = "telephone"; // "telephone" | "pin"

// Connexion
function connecter() {
  if (etapeAuth === "telephone") {
    const tel = document.getElementById("inp-tel").value.trim();
    if (!tel || tel.length < 8) {
      alert("Veuillez entrer un numero de telephone valide.");
      return;
    }
    telephone = tel;
    // Passer a l'etape PIN
    document.getElementById("pin-group").style.display = "block";
    document.getElementById("btn-connect").textContent = "Confirmer le PIN";
    etapeAuth = "pin";
    document.getElementById("inp-pin").focus();
    return;
  }

  // Etape PIN — creer session et ouvrir WebSocket
  const pin = document.getElementById("inp-pin").value.trim();
  if (!pin || pin.length !== 4) {
    alert("Le PIN doit contenir exactement 4 chiffres.");
    return;
  }

  // Generer ID de session
  idSession = "sess_" + Date.now() + "_" + Math.random().toString(36).slice(2, 7);

  // Ouvrir WebSocket
  ouvrirWebSocket(pin);
}

function ouvrirWebSocket(pin) {
  const wsUrl = `${WS_BASE}/chat/ws/${idSession}/${encodeURIComponent(telephone)}`;
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    document.getElementById("chat-status").textContent = "Connecte — entrez votre PIN";
    // Envoyer le PIN comme premier message
    ws.send(JSON.stringify({ message: pin }));
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    gererReponse(data);
  };

  ws.onerror = (e) => {
    ajouterMessage("bot", "Erreur de connexion au serveur. Verifiez que le backend tourne sur localhost:8000.", "error");
  };

  ws.onclose = () => {
    document.getElementById("chat-status").textContent = "Deconnecte";
    document.getElementById("btn-send").disabled = true;
    document.getElementById("inp-msg").disabled = true;
  };
}

function deconnecter() {
  if (ws) ws.close();
  authenticated = false;
  etapeAuth = "telephone";
  telephone = null;
  idSession = null;

  document.getElementById("client-info").style.display = "none";
  document.getElementById("session-info").style.display = "none";
  document.getElementById("ticket-info").style.display = "none";
  document.getElementById("pin-group").style.display = "none";
  document.getElementById("btn-connect").textContent = "Se connecter";
  document.getElementById("inp-tel").value = "";
  document.getElementById("inp-pin").value = "";
  document.getElementById("btn-send").disabled = true;
  document.getElementById("inp-msg").disabled = true;
  document.getElementById("chat-status").textContent = "En attente de connexion...";

  ajouterMessage("bot", "Vous avez ete deconnecte. Entrez votre numero pour vous reconnecter.");
}

// Envoi message
function envoyerMessage() {
  const inp = document.getElementById("inp-msg");
  const msg = inp.value.trim();
  if (!msg || !ws || ws.readyState !== WebSocket.OPEN) return;

  ajouterMessage("user", msg);
  ws.send(JSON.stringify({ message: msg }));
  inp.value = "";

  // Afficher indicateur de frappe
  afficherTyping(true);

  // Vider les suggestions rapides
  document.getElementById("quick-replies").innerHTML = "";
}

// Gestion reponses
function gererReponse(data) {
  afficherTyping(false);

  if (data.type === "connexion") {
    document.getElementById("chat-status").textContent = "En cours d'authentification...";
    return;
  }

  if (data.type === "frappe") return;

  if (data.type === "erreur") {
    ajouterMessage("bot", "Erreur : " + data.message, "error");
    return;
  }

  if (data.type === "info") {
    ajouterMessage("bot", data.message, "info");
    return;
  }

  if (data.type === "reponse") {
    // Authentification reussie
    if (data.authentifie === true && data.client) {
      authenticated = true;
      mettreAJourProfil(data.client);
      document.getElementById("client-info").style.display = "block";
      document.getElementById("session-info").style.display = "block";
      document.getElementById("chat-status").textContent = "Connecte";
      document.getElementById("btn-send").disabled = false;
      document.getElementById("inp-msg").disabled = false;
      document.getElementById("inp-msg").focus();
    }

    // Mettre a jour les infos de session
    if (data.intention) document.getElementById("ss-intent").textContent = data.intention.replace(/_/g, " ");
    if (data.sentiment) document.getElementById("ss-sent").textContent = data.sentiment;
    if (data.langue) {
      const lb = document.getElementById("lang-badge");
      lb.innerHTML = `<span class="badge badge-green">${data.langue.toUpperCase()}</span>`;
    }

    // Afficher la reponse
    const style = data.escalade ? (data.priorite === "P1" ? "urgent" : "escalade") : "";
    ajouterMessage("bot", data.reponse, style);

    // Tickets
    if (data.id_ticket) {
      ajouterTicket(data.id_ticket, data.priorite, data.regle_escalade);
    }

    // Suggestions rapides selon l'intention
    afficherSuggestions(data.intention);
  }
}

// Helpers
function ajouterMessage(role, texte, style = "") {
  const zone = document.getElementById("messages");
  const div = document.createElement("div");
  div.className = `message message-${role}`;

  const bubble = document.createElement("div");
  bubble.className = `message-bubble ${style}`;
  bubble.textContent = texte;

  const time = document.createElement("div");
  time.className = "message-time";
  time.textContent = new Date().toLocaleTimeString("fr-FR", {hour: "2-digit", minute: "2-digit"});

  div.appendChild(bubble);
  div.appendChild(time);
  zone.appendChild(div);
  zone.scrollTop = zone.scrollHeight;
}

function afficherTyping(visible) {
  const existant = document.getElementById("typing-indicator");
  if (visible && !existant) {
    const zone = document.getElementById("messages");
    const div = document.createElement("div");
    div.className = "message message-bot";
    div.id = "typing-indicator";
    div.innerHTML = `<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>`;
    zone.appendChild(div);
    zone.scrollTop = zone.scrollHeight;
  } else if (!visible && existant) {
    existant.remove();
  }
}

function mettreAJourProfil(client) {
  document.getElementById("cl-nom").textContent = client.nom || "—";
  document.getElementById("cl-op").textContent = client.operateur || "—";
  document.getElementById("cl-seg").textContent = client.segment || "—";
}

function ajouterTicket(id, priorite, type) {
  document.getElementById("ticket-info").style.display = "block";
  const liste = document.getElementById("tickets-list");
  const card = document.createElement("div");
  card.className = "ticket-card";
  card.innerHTML = `
    <div class="ticket-id">${id}</div>
    <div class="ticket-meta">Priorite ${priorite || "P3"} — ${(type || "reclamation").replace(/_/g, " ")}</div>
    <a href="${API_BASE.replace("/api/v1","")}/api/v1/rapports/${id}/pdf" target="_blank" style="font-size:0.75rem;color:var(--bleu)">Telecharger PDF</a>
  `;
  liste.prepend(card);
}

function afficherSuggestions(intention) {
  const suggestions = {
    "consulter_solde": ["Voir mon historique", "Signaler un probleme", "Parler a un conseiller"],
    "transaction_non_recue": ["Donner la reference", "Demander un remboursement"],
    "retrait_echoue": ["Trouver un autre agent", "Demander le remboursement"],
    "frais_et_limites": ["Relever mes limites", "Autre question"],
    "salutation": ["Voir mon solde", "Signaler une transaction", "Questions frequentes"],
  };
  const zone = document.getElementById("quick-replies");
  zone.innerHTML = "";
  const items = suggestions[intention] || [];
  items.forEach(item => {
    const btn = document.createElement("button");
    btn.className = "quick-reply-btn";
    btn.textContent = item;
    btn.onclick = () => {
      document.getElementById("inp-msg").value = item;
      envoyerMessage();
    };
    zone.appendChild(btn);
  });
}