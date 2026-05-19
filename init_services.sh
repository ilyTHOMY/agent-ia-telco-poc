#!/usr/bin/env bash
# =============================================================================
# Script de setup complet des services — PostgreSQL, Redis, Qdrant
# + indexation RAG (embeddings FAQ dans Qdrant)
# + telechargement du modele d'embedding sentence-transformers
# A executer UNE SEULE FOIS apres docker-compose up --build
# Usage : ./init_services.sh
# =============================================================================

set -euo pipefail
echo ""
echo "  Setup complet Agent IA Telco v2"
echo "=================================================="

# ── Verifier que Docker tourne ───────────────────────────────────────────────
if ! docker info > /dev/null 2>&1; then
  echo "ERREUR : Docker n'est pas demarre. Lance Docker Desktop d'abord."
  exit 1
fi

# ── Verifier que les containers sont up ──────────────────────────────────────
echo "[1/6] Verification des services Docker..."
SERVICES=("backend" "postgres" "redis" "qdrant")
for svc in "${SERVICES[@]}"; do
  STATUS=$(docker-compose ps --format json 2>/dev/null | python3 -c "
import sys, json
data = sys.stdin.read()
for line in data.strip().split('\n'):
    try:
        obj = json.loads(line)
        if '$svc' in obj.get('Service', ''):
            print(obj.get('State', 'unknown'))
            break
    except: pass
" 2>/dev/null || echo "unknown")
  echo "  $svc : $STATUS"
done

# ── Attendre que PostgreSQL soit pret ─────────────────────────────────────────
echo "[2/6] Attente PostgreSQL..."
RETRIES=20
until docker-compose exec -T postgres pg_isready -U agentia -d agentia > /dev/null 2>&1; do
  RETRIES=$((RETRIES-1))
  if [ $RETRIES -le 0 ]; then
    echo "ERREUR : PostgreSQL ne repond pas apres 20 tentatives."
    exit 1
  fi
  echo "  En attente... ($RETRIES restants)"
  sleep 3
done
echo "  PostgreSQL pret."

# ── Creer les tables PostgreSQL ───────────────────────────────────────────────
echo "[3/6] Creation des tables PostgreSQL..."
docker-compose exec -T postgres psql -U agentia -d agentia << 'SQLEOF'
-- Table des tickets de reclamation
CREATE TABLE IF NOT EXISTS tickets (
    id VARCHAR(50) PRIMARY KEY,
    id_client VARCHAR(50),
    telephone VARCHAR(20) NOT NULL,
    type_reclamation VARCHAR(100),
    description TEXT,
    priorite VARCHAR(5) DEFAULT 'P3',
    statut VARCHAR(30) DEFAULT 'ouvert',
    canal_origine VARCHAR(30),
    id_transaction VARCHAR(100),
    date_ouverture TIMESTAMPTZ DEFAULT NOW(),
    date_mise_a_jour TIMESTAMPTZ DEFAULT NOW(),
    date_cloture TIMESTAMPTZ,
    agent_assigne VARCHAR(100),
    sla_heures INTEGER DEFAULT 24
);

-- Table de l'historique des conversations
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    id_session VARCHAR(100) NOT NULL,
    telephone VARCHAR(20) NOT NULL,
    canal VARCHAR(30) DEFAULT 'chat',
    role VARCHAR(20) NOT NULL,
    contenu TEXT NOT NULL,
    intention VARCHAR(100),
    sentiment VARCHAR(30),
    langue VARCHAR(10),
    horodatage TIMESTAMPTZ DEFAULT NOW()
);

-- Table des sessions clients
CREATE TABLE IF NOT EXISTS sessions (
    id_session VARCHAR(100) PRIMARY KEY,
    telephone VARCHAR(20) NOT NULL,
    canal VARCHAR(30),
    authentifie BOOLEAN DEFAULT FALSE,
    langue VARCHAR(10) DEFAULT 'fr',
    escalade_effectuee BOOLEAN DEFAULT FALSE,
    date_debut TIMESTAMPTZ DEFAULT NOW(),
    date_derniere_activite TIMESTAMPTZ DEFAULT NOW()
);

-- Table des notifications envoyees
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    canal VARCHAR(20) NOT NULL,
    telephone VARCHAR(20) NOT NULL,
    message TEXT,
    id_ticket VARCHAR(50),
    statut VARCHAR(20) DEFAULT 'envoye',
    horodatage TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour les requetes frequentes
CREATE INDEX IF NOT EXISTS idx_tickets_telephone ON tickets(telephone);
CREATE INDEX IF NOT EXISTS idx_tickets_statut ON tickets(statut);
CREATE INDEX IF NOT EXISTS idx_tickets_priorite ON tickets(priorite);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(id_session);
CREATE INDEX IF NOT EXISTS idx_sessions_telephone ON sessions(telephone);

SELECT 'Tables creees avec succes.' AS resultat;
SQLEOF
echo "  Tables PostgreSQL creees."

# ── Verifier Redis ────────────────────────────────────────────────────────────
echo "[4/6] Test Redis..."
REDIS_PONG=$(docker-compose exec -T redis redis-cli PING 2>/dev/null || echo "FAILED")
if [ "$REDIS_PONG" = "PONG" ]; then
  echo "  Redis repond : PONG"
else
  echo "  AVERTISSEMENT : Redis ne repond pas. Les sessions tourneront en memoire."
fi

# ── Verifier Qdrant ───────────────────────────────────────────────────────────
echo "[5/6] Test Qdrant..."
QDRANT_STATUS=$(curl -s http://localhost:6333/healthz 2>/dev/null || echo "FAILED")
if echo "$QDRANT_STATUS" | grep -q "ok\|true\|200" 2>/dev/null || [ -n "$QDRANT_STATUS" ]; then
  echo "  Qdrant repond. Dashboard : http://localhost:6333/dashboard"
else
  echo "  AVERTISSEMENT : Qdrant ne repond pas encore (normal si vient de demarrer)."
  echo "  Attente supplementaire..."
  sleep 5
fi

# ── Indexation RAG ────────────────────────────────────────────────────────────
echo "[6/6] Indexation de la base de connaissances RAG dans Qdrant..."
echo "  (Telechargement du modele sentence-transformers si premiere fois...)"
echo "  Cela peut prendre 2 a 5 minutes au premier lancement."
echo ""

docker-compose exec -T backend python -m ai_core.rag.indexer --reinit 2>&1 | while IFS= read -r line; do
  echo "  $line"
done

echo ""
echo "=================================================="
echo "  SETUP TERMINE"
echo ""
echo "  Services disponibles :"
echo "  Frontend     : http://localhost:3000"
echo "  API Swagger  : http://localhost:8000/docs"
echo "  Qdrant       : http://localhost:6333/dashboard"
echo ""
echo "  Pour relancer uniquement l'indexation RAG :"
echo "  docker-compose exec backend python -m ai_core.rag.indexer"
echo ""
echo "  Pour reinitialiser completement Qdrant :"
echo "  docker-compose exec backend python -m ai_core.rag.indexer --reinit"
echo "=================================================="
