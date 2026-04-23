// ── Client API centralisé pour le frontend ─────────────────────────────────
const API_BASE = "http://localhost:8000/api/v1";

const api = {
  async get(path) {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async post(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async pdfUrl(idTicket) {
    return `${API_BASE}/rapports/${idTicket}/pdf`;
  }
};