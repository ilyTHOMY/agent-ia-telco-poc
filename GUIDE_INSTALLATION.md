# Guide d'installation complet — Agent IA Support Telco v2

## Prerequis

- Windows 10/11 avec Docker Desktop installe et demarre
- Git Bash installe
- Python 3.11 installe (`py -3.11 --version` doit repondre)
- Compte Google AI Studio (gratuit) : https://aistudio.google.com

---

## Etape 1 — Initialiser la structure du projet

```bash
chmod +x init_poc_v2.sh && ./init_poc_v2.sh
cd agent-ia-telco-poc-v2
```

## Etape 2 — Copier tous les fichiers generes

Placer chaque fichier dans le bon dossier selon le tableau :

| Fichier                        | Destination                          |
|--------------------------------|--------------------------------------|
| clients.json                   | data/                                |
| transactions.json              | data/                                |
| agents.json                    | data/                                |
| mobile_money_api_updated.py    | backend/mocks/mobile_money_api.py    |
| agents_network.py              | backend/mocks/                       |
| crm_api.py                     | backend/mocks/                       |
| notifications.py               | backend/mocks/                       |
| whatsapp_api.py                | backend/mocks/                       |
| ussd_api.py                    | backend/mocks/                       |
| email_api.py                   | backend/mocks/                       |
| auth_otp.py                    | backend/services/                    |
| rapport.py                     | backend/services/                    |
| db_database.py                 | backend/db/database.py               |
| db_schemas.py                  | backend/db/schemas.py                |
| main_v2.py                     | backend/main.py                      |
| routes_chat.py                 | backend/api/                         |
| routes_dashboard.py            | backend/api/                         |
| routes_canaux.py               | backend/api/                         |
| routes_rapports.py             | backend/api/                         |
| language_detect.py             | ai_core/nlu/                         |
| sentiment.py                   | ai_core/nlu/                         |
| entity_extractor.py            | ai_core/nlu/                         |
| intent_classifier.py           | ai_core/nlu/                         |
| intents_fr.json                | ai_core/nlu/intents_dataset/         |
| intents_wo.json                | ai_core/nlu/intents_dataset/         |
| faq_wave.md                    | ai_core/rag/docs/                    |
| faq_orange_money.md            | ai_core/rag/docs/                    |
| faq_mixx.md                    | ai_core/rag/docs/                    |
| reglementation_bceao.md        | ai_core/rag/docs/                    |
| knowledge_base.py              | ai_core/rag/                         |
| vector_store.py                | ai_core/rag/                         |
| indexer.py                     | ai_core/rag/                         |
| retriever.py                   | ai_core/rag/                         |
| context_manager.py             | ai_core/dialogue/                    |
| escalade_engine.py             | ai_core/dialogue/                    |
| orchestrateur.py               | ai_core/dialogue/                    |
| system_prompt.txt              | ai_core/prompts/                     |
| variables_updated.css          | frontend/css/variables.css           |
| main.css                       | frontend/css/                        |
| chat.css                       | frontend/css/                        |
| dashboard.css                  | frontend/css/                        |
| chat.html                      | frontend/pages/                      |
| dashboard.html                 | frontend/pages/                      |
| ussd.html                      | frontend/pages/                      |
| whatsapp.html                  | frontend/pages/                      |
| scenarios.html                 | frontend/pages/                      |
| api.js                         | frontend/js/                         |
| chat.js                        | frontend/js/                         |
| dashboard.js                   | frontend/js/                         |
| scenarios.js                   | frontend/js/                         |
| test_nlu.py                    | tests/                               |
| test_escalade.py               | tests/                               |
| test_mocks.py                  | tests/                               |
| test_scenarios_e2e.py          | tests/                               |

## Etape 3 — Configurer le .env

```bash
cp .env.example .env
```

Editer `.env` et renseigner :
```
GOOGLE_API_KEY=AIza...  # Votre cle Google AI Studio
```

Les autres variables peuvent rester par defaut pour le developpement local.

## Etape 4 — Lancer Docker

```bash
docker-compose up --build
```

Attendre que les 5 services soient demarres (environ 2-3 minutes au premier lancement).

## Etape 5 — Initialiser les services

**Dans un nouveau terminal Git Bash :**

```bash
cd agent-ia-telco-poc-v2
chmod +x init_services.sh && ./init_services.sh
```

Ce script :
1. Cree les tables PostgreSQL
2. Verifie Redis et Qdrant
3. Telecharge le modele d'embedding (sentence-transformers, ~90 Mo)
4. Vectorise les 4 documents FAQ dans Qdrant

**Premiere execution : 5 a 10 minutes** (telechargement du modele)

## Acces aux services

| Service        | URL                                |
|----------------|------------------------------------|
| Frontend chat  | http://localhost:3000/pages/chat.html |
| Dashboard      | http://localhost:3000/pages/dashboard.html |
| USSD simulator | http://localhost:3000/pages/ussd.html |
| WhatsApp mock  | http://localhost:3000/pages/whatsapp.html |
| Scenarios demo | http://localhost:3000/pages/scenarios.html |
| API Swagger    | http://localhost:8000/docs |
| Qdrant dashboard | http://localhost:6333/dashboard |

## Lancer les tests

```bash
# Dans le container backend
docker-compose exec backend pytest tests/ -v

# Ou localement avec le venv active
py -3.11 -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
PYTHONPATH=. pytest tests/ -v
```

## Comptes de test disponibles

| Telephone        | PIN  | Operateur    | Langue | Notes           |
|------------------|------|--------------|--------|-----------------|
| +221771234567    | 1234 | Wave         | FR     | Scenario S1, S2 |
| +221772345678    | 5678 | Wave         | WO     | Wolof pur       |
| +221773456789    | 2222 | Wave         | FR-WO  | KYC incomplet   |
| +221781234567    | 9999 | Orange Money | FR     | Premium S2      |
| +221782345678    | 3333 | Orange Money | FR     | Solde 0         |
| +221783456789    | 4444 | Orange Money | WO     | Scenario S4     |
| +221761234567    | 7777 | Mixx by Yas  | FR     | Premium + carte |
| +221762345678    | 6666 | Mixx by Yas  | FR-WO  | Standard        |
| +221774567890    | 1111 | Wave         | FR-WO  | Scenario S3     |
| +221784567890    | 8888 | Orange Money | WO     | Scenario S5     |

## Commandes utiles

```bash
# Logs backend en temps reel
docker-compose logs -f backend

# Reinitialiser Qdrant (reindexer les FAQ)
docker-compose exec backend python -m ai_core.rag.indexer --reinit

# Acceder au shell backend
docker-compose exec backend bash

# Reinitialiser la base PostgreSQL
docker-compose exec postgres psql -U agentia -d agentia -c "TRUNCATE tickets, conversations, sessions CASCADE;"

# Arreter tous les services
docker-compose down

# Tout supprimer (volumes inclus)
docker-compose down -v
```
