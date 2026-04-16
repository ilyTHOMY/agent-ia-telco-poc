# Agent IA Support Telco / Mobile Money — PoC v2

Agent conversationnel IA omnicanal pour le support client Mobile Money UEMOA.

## Stack

| Couche       | Technologie                              |
|--------------|------------------------------------------|
| Backend API  | FastAPI + Python 3.11                    |
| LLM          | Gemini 2.5 Flash (Google AI Studio)      |
| RAG          | Qdrant + sentence-transformers           |
| Frontend     | HTML + CSS + JavaScript pur              |
| BDD          | PostgreSQL 15 + Redis 7                  |
| Infra        | Docker Compose                           |

## Canaux

| Canal      | Statut          |
|------------|-----------------|
| Web Chat   | WebSocket reel  |
| WhatsApp   | API Meta reelle |
| USSD       | Simule          |
| Email      | SendGrid reel   |
| App mobile | Simule via web  |

## Demarrage

```bash
cp .env.example .env
# Renseigner GOOGLE_API_KEY dans .env
docker-compose up --build
```

- Frontend : http://localhost:3000
- API docs : http://localhost:8000/docs
- Qdrant   : http://localhost:6333/dashboard

## Perimetre PoC (section 7 note de cadrage)

- [x] Agent IA multicanal (Web, WA, USSD, Email)
- [x] NLU francais + wolof + franco-wolof
- [x] Base RAG : FAQ Wave, Orange Money, Mixx
- [x] API mock : transactions, solde, agents, CRM
- [x] Moteur escalade 6 regles metier
- [x] Rapports incidents PDF + JSON
- [x] Dashboard operateur temps reel
- [x] 6 scenarios de demonstration cliquables
- [x] Documentation technique
