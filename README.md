# Agent IA Support Client — Mobile Money UEMOA

Agent conversationnel IA omnicanal pour le support client Mobile Money en zone UEMOA. Couvre Wave, Orange Money (Sonatel) et Mixx by Yas (Axian). Supporte le français, le wolof et le franco-wolof.

---

## Aperçu

L'agent traite automatiquement 70% des demandes clients sans intervention humaine - consultation de solde, FAQ tarifaire, signalement de transactions, localisation d'agents réseau. Les cas complexes sont escaladés vers des conseillers humains avec création automatique de ticket et notification email au support.

**Canaux supportés :** Web Chat · Telegram

> **Note :** L'email n'est pas un canal de conversation. Il sert uniquement à notifier l'équipe support lors de la création d'un ticket d'escalade.

---

## Stack technique

| Composant | Technologie |
|---|---|
| LLM | Gemini 2.5 Flash (Google AI Studio) |
| RAG | Qdrant + sentence-transformers |
| Backend | FastAPI · Python 3.11 |
| Base de données | PostgreSQL 15 · Redis 7 |
| Frontend | HTML / CSS / JS · nginx |
| Infra | Docker Compose |
| Notifications | Gmail SMTP (tickets uniquement) |
| Messaging | Telegram Bot API · ngrok |

---

## Prérequis

- Docker Desktop (Windows/Mac/Linux)
- Git
- Compte Google AI Studio - clé API gratuite sur [aistudio.google.com](https://aistudio.google.com)
- Compte Gmail avec mot de passe d'application (pour les notifications de tickets)
- ngrok (optionnel, pour Telegram)

---

## Installation

### 1. Cloner le projet

```bash
git clone https://github.com/ton-compte/agent-ia-telco-poc.git
cd agent-ia-telco-poc
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Ouvrir `.env` et renseigner :

```env
# LLM
GOOGLE_API_KEY=AIza...

# Accès admin dashboard
ADMIN_USERNAME=
ADMIN_PASSWORD=

# Notifications email (tickets uniquement - pas un canal de chat)
GMAIL_USER=ton.email@gmail.com
GMAIL_APP_PASSWORD=xxxxxxxxxxxx   # 16 caractères sans espaces
EMAIL_DESTINATAIRE=ton.email@gmail.com

# Telegram (optionnel)
TELEGRAM_BOT_TOKEN=
```

> **Gmail App Password :** Va sur myaccount.google.com → Sécurité → Validation en deux étapes (activer) → Mots de passe des applications → Générer. Copie les 16 caractères **sans espaces**.

### 3. Lancer Docker

```bash
docker-compose up --build
```

Attendre que tous les services soient démarrés (environ 2-3 minutes au premier lancement).

### 4. Initialiser la base de données et indexer les FAQ

```bash
# Linux / Mac / Git Bash
chmod +x init_services.sh && ./init_services.sh
```

Ce script crée les tables PostgreSQL et indexe les documents FAQ dans Qdrant (70 chunks - Wave, Orange Money, Mixx, BCEAO).

### 5. Accéder à l'application

| Interface | URL |
|---|---|
| Chat Web | http://localhost:3000/pages/chat.html |
| Dashboard | http://localhost:3000/pages/dashboard.html |
| Scénarios | http://localhost:3000/pages/scenarios.html |
| API Swagger | http://localhost:8000/docs |
| Qdrant Dashboard | http://localhost:6333/dashboard |

---

## Création de compte (nouveau client)

Sur le Chat Web, cliquer sur l'onglet **"Inscription"** dans la sidebar. Le client renseigne :

- **Nom complet**
- **Numéro de téléphone** (+221...)
- **Opérateur** — Wave, Orange Money ou Mixx by Yas (choix manuel)
- **Code PIN** (4 chiffres, choisi librement)
- **Confirmer le PIN**

Le compte est créé immédiatement avec les limites BCEAO niveau 1 (100 000 XOF/jour). Une vérification KYC dans l'application de l'opérateur permet d'augmenter ces limites.

Sur **Telegram**, le bot guide le client étape par étape :
```
/start → Entrer le numéro (+221...) → Entrer le PIN
```
Si le numéro est inconnu, un profil est créé automatiquement avec le PIN choisi.

---

## Comptes de test

| Téléphone | PIN | Opérateur | Profil | Usage |
|---|---|---|---|---|
| +221771234567 | 1234 | Wave | Moussa Diallo — vérifié 500k/jour | S1 — Historique & frais |
| +221779876543 | 5678 | Wave | Ibrahima Seck — vérifié 500k/jour | S2 — Transfert bloqué P1 |
| +221781111222 | 2222 | Orange Money | Fatou Ndiaye — non vérifié 100k/jour | S3 — KYC plafond |
| +221781234567 | 9999 | Orange Money | Aminata Cisse — vérifiée 500k/jour | S4 — Litige agent P2 |
| +221761234567 | 7777 | Mixx by Yas | Oumy Sarr — vérifiée + carte Mastercard | S5 — Carte Mixx |
| +221769876543 | 3333 | Mixx by Yas | Cheikh Fall — vérifié 500k/jour | S6 — Transfert bloqué P2 |
| +221775859720 | 0000 | Wave | Thomas Thiaw — vérifié 500k/jour | Tests libres |
| Nouveau numéro | PIN choisi | Choix libre | Création automatique | Inscription |

---

## Dashboard opérateur

Accessible sur http://localhost:3000/pages/dashboard.html

**Accès lecture seule** - cliquer sur "Accès lecture seule" sans login. Permet de voir les KPIs et tickets mais pas de les modifier.

**Accès admin** - identifiants configurés dans `.env` :
```
ADMIN_USERNAME=admin
ADMIN_PASSWORD=agentia2026
```

En mode admin, les boutons "En cours" et "Résoudre" apparaissent dans le tableau des tickets. Un modal permet d'assigner un agent, changer le statut et ajouter une note interne.

---

## Notifications email (tickets uniquement)

Quand un ticket est créé par escalade, un email HTML est automatiquement envoyé à l'adresse `EMAIL_DESTINATAIRE` avec :
- Référence du ticket
- Type et priorité (P1/P2/P3)
- Téléphone du client
- Description
- SLA de traitement
- Liens vers le dashboard et le rapport PDF

> L'email ne permet pas de chatter avec le bot. C'est un canal de notification interne uniquement.

---

## Telegram Bot

### Setup

1. Créer un bot via `@BotFather` sur Telegram → `/newbot`
2. Copier le token dans `.env` : `TELEGRAM_BOT_TOKEN=xxxx`
3. Rebuild le backend : `docker-compose up --build backend`
4. Lancer ngrok : `ngrok http 8000`
5. Enregistrer le webhook :
```bash
curl "https://api.telegram.org/botTON_TOKEN/setWebhook?url=https://TON_URL_NGROK/api/v1/canaux/telegram/webhook"
```
6. Ouvrir le bot et envoyer `/start`

### Flux

```
/start
→ Entrer le numéro de téléphone (+221...)
→ Entrer le PIN (4 chiffres)
→ Conversation normale avec l'agent IA
```

---

## Architecture

```
┌─────────────────────────────────────┐
│             CANAUX                  │
│     Web Chat · Telegram             │
└──────────────┬──────────────────────┘
               │ WebSocket / REST
┌──────────────▼──────────────────────┐
│          FASTAPI BACKEND            │
│  routes_chat · routes_dashboard     │
│  routes_canaux · routes_rapports    │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         ORCHESTRATEUR IA            │
│  NLU → Intent + Entity + Sentiment  │
│  RAG → Qdrant (70 chunks FAQ)       │
│  LLM → Gemini 2.5 Flash             │
│  Escalade → 5 règles P1/P2          │
└──────┬───────────────────┬──────────┘
       │                   │
┌──────▼──────┐    ┌───────▼──────────┐
│   DONNÉES   │    │    SERVICES      │
│ clients.json│    │ Email Gmail SMTP │
│ tickets.json│    │ Rapport PDF      │
│ agents.json │    │ Notifications    │
│ PostgreSQL  │    └──────────────────┘
│ Redis       │
└─────────────┘
```

---

## Fonctionnalités

### Résolution autonome N1 (70%)
- Consultation de solde en temps réel
- Réponses FAQ depuis la base de connaissances RAG (Wave, Orange Money, Mixx, BCEAO)
- Localisation d'agents réseau par quartier
- Procédures KYC et gestion de compte

### Escalade intelligente
| Priorité | SLA | Déclencheur |
|---|---|---|
| P1 | 5 min | Fraude, SIM swap, montant > 500 000 XOF |
| P2 | 4h | Frustration client, litige agent, 2 incompréhensions consécutives |
| P3 | 24h | PIN oublié, demandes KYC |

### Support multilingue
- Français (fr)
- Wolof (wo)
- Franco-wolof (fr-wo) - détection et adaptation automatiques

### Rapports PDF
Chaque ticket génère un rapport PDF incluant les infos du ticket, l'historique des actions et l'historique complet de la conversation client.

---

## Limites Gemini Free Tier

| Modèle | RPM | RPD | Reset |
|---|---|---|---|
| gemini-2.5-flash | 10/min | 250/jour | Minuit heure Pacifique |
| gemini-2.5-flash-lite | 15/min | 1 000/jour | Minuit heure Pacifique |

---

## Commandes utiles

```bash
# Démarrer
docker-compose up --build

# Arrêter
docker-compose down

# Logs backend en temps réel
docker-compose logs -f backend

# Réindexer les FAQ dans Qdrant
docker-compose exec backend python -m ai_core.rag.indexer --reinit

# Lancer les tests
docker-compose exec backend pytest tests/ -v

# Vérifier Gemini
docker-compose exec backend python -c "
import google.generativeai as genai, os
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
print(genai.GenerativeModel('gemini-2.5-flash').generate_content('ping').text)
"

# Vider les tickets pour une démo propre
echo '{\"tickets\":[]}' > data/tickets.json
```

---

## Structure du projet

```
agent-ia-telco-poc/
├── backend/
│   ├── api/              # Routes FastAPI (chat, dashboard, canaux, rapports, auth)
│   ├── db/               # PostgreSQL schemas et CRUD
│   ├── mocks/            # APIs simulées (mobile money, CRM, agents réseau)
│   ├── models/           # Modèles Pydantic
│   └── services/         # Email Gmail, rapport PDF, notifications
├── ai_core/
│   ├── dialogue/         # Orchestrateur v5, context manager, moteur d'escalade
│   ├── nlu/              # Classifier, entity extractor, sentiment, langue
│   ├── prompts/          # System prompt, contexte wolof
│   ├── rag/              # Retriever Qdrant, indexer, vector store
│   └── wolof/            # Dictionnaire et expressions Mobile Money
├── data/
│   ├── clients.json      # Profils clients (test + nouveaux inscrits)
│   ├── transactions.json # Transactions simulées
│   ├── agents.json       # Réseau agents par quartier/ville
│   └── tickets.json      # Tickets créés et persistés
├── frontend/
│   ├── pages/            # Chat, Dashboard, Scénarios
│   ├── js/               # Scripts et theme toggle
│   └── favicon.svg       # Logo application
├── tests/                # Tests unitaires NLU, escalade, auth
├── docker/               # Dockerfiles et nginx.conf
├── docker-compose.yml
├── requirements.txt
└── .env.example
```