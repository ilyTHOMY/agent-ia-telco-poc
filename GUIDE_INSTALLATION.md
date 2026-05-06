# Guide de placement — Tous les fichiers du projet

## Structure finale attendue

```
agent-ia-telco-poc-v2/
├── docker-compose.yml          ← docker_compose_final.yml
├── .env.example / .env
├── requirements.txt
├── pytest.ini
├── README.md
├── init_services.sh
│
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend     ← Dockerfile_frontend_v2
│   └── nginx.conf              ← nginx.conf
│
├── data/
│   ├── clients.json            ← REMPLACE par clients.json v2 (avec PINs, sans signalements)
│   ├── transactions.json
│   ├── agents.json
│   └── tickets.json
│
├── backend/
│   ├── main.py                 ← main_v2.py
│   ├── config.py
│   ├── api/
│   │   ├── routes_chat.py
│   │   ├── routes_dashboard.py
│   │   ├── routes_canaux.py
│   │   └── routes_rapports.py
│   ├── services/
│   │   ├── conversation.py     ← conversation_service.py
│   │   ├── ticket.py           ← ticket_service.py
│   │   ├── notification.py     ← notification_service.py
│   │   ├── rapport.py
│   │   └── auth_otp.py
│   ├── mocks/
│   │   ├── mobile_money_api.py ← mobile_money_api_updated.py
│   │   ├── agents_network.py
│   │   ├── crm_api.py
│   │   ├── notifications.py
│   │   ├── whatsapp_api.py
│   │   ├── ussd_api.py
│   │   └── email_api.py
│   ├── models/                 (dossier vide OK pour le PoC)
│   └── db/
│       ├── database.py         ← db_database.py
│       ├── schemas.py          ← db_schemas.py
│       └── crud.py
│
├── ai_core/
│   ├── nlu/
│   │   ├── intent_classifier.py
│   │   ├── entity_extractor.py
│   │   ├── sentiment.py
│   │   ├── language_detect.py
│   │   └── intents_dataset/
│   │       ├── intents_fr.json
│   │       └── intents_wo.json
│   ├── rag/
│   │   ├── knowledge_base.py
│   │   ├── vector_store.py
│   │   ├── indexer.py
│   │   ├── retriever.py
│   │   └── docs/
│   │       ├── faq_wave.md         ← version mise a jour 2025
│   │       ├── faq_orange_money.md ← version mise a jour 2025
│   │       ├── faq_mixx.md         ← version mise a jour 2025
│   │       └── reglementation_bceao.md
│   ├── dialogue/
│   │   ├── orchestrateur.py
│   │   ├── context_manager.py
│   │   ├── escalade_engine.py
│   │   └── response_generator.py
│   ├── prompts/
│   │   ├── system_prompt.txt
│   │   ├── escalade_prompt.txt
│   │   ├── rapport_prompt.txt
│   │   ├── ussd_prompt.txt
│   │   └── wolof_context.txt
│   └── wolof/
│       ├── dictionnaire.json
│       └── expressions_mobile_money.json
│
├── frontend/
│   ├── index.html              ← index_v2.html
│   ├── css/
│   │   ├── variables.css       ← variables_updated.css
│   │   ├── main.css
│   │   ├── chat.css
│   │   └── dashboard.css
│   ├── js/
│   │   ├── api.js
│   │   ├── chat.js
│   │   ├── dashboard.js
│   │   ├── scenarios.js
│   │   └── rapport.js          ← rapport_js.js
│   ├── pages/
│   │   ├── chat.html           ← chat_v2.html     (BEAU)
│   │   ├── dashboard.html      ← dashboard_v2.html (BEAU)
│   │   ├── ussd.html           ← ussd_v2.html     (BEAU)
│   │   ├── whatsapp.html       ← whatsapp_v2.html (BEAU)
│   │   └── scenarios.html      ← scenarios_v2.html (BEAU)
│   └── scenarios/
│       ├── scenario1_faq.js
│       ├── scenario2_transaction.js
│       ├── scenario3_fraude.js
│       ├── scenario4_agent.js
│       ├── scenario5_ussd.js
│       └── scenario6_dashboard.js
│
└── tests/
    ├── __init__.py
    ├── test_nlu.py
    ├── test_escalade.py
    ├── test_mocks.py
    ├── test_canaux.py
    └── test_scenarios_e2e.py
```

## Ordre de mise en place

1. `chmod +x init_poc_v2.sh && ./init_poc_v2.sh`
2. Copier tous les fichiers selon la structure ci-dessus
3. `cp .env.example .env` et renseigner `GOOGLE_API_KEY`
4. `docker-compose up --build`
5. `chmod +x init_services.sh && ./init_services.sh` (dans un autre terminal)
6. Ouvrir `http://localhost:3000`

## Verification rapide

```bash
# Backend sain
curl http://localhost:8000/health

# Qdrant actif
curl http://localhost:6333/healthz

# Redis actif
docker-compose exec redis redis-cli PING

# PostgreSQL actif
docker-compose exec postgres pg_isready -U agentia

# Lancer tous les tests
docker-compose exec backend pytest tests/ -v
```

## Comptes de test

| Telephone        | PIN  | Operateur    | Langue | Scenario |
|------------------|------|--------------|--------|----------|
| +221771234567    | 1234 | Wave         | FR     | S1, S2   |
| +221772345678    | 5678 | Wave         | WO     | WO pur   |
| +221773456789    | 2222 | Wave         | FR-WO  | KYC -    |
| +221781234567    | 9999 | Orange Money | FR     | S2       |
| +221782345678    | 3333 | Orange Money | FR     | Solde 0  |
| +221783456789    | 4444 | Orange Money | WO     | S4       |
| +221761234567    | 7777 | Mixx by Yas  | FR     | Premium  |
| +221762345678    | 6666 | Mixx by Yas  | FR-WO  | Standard |
| +221774567890    | 1111 | Wave         | FR-WO  | S3       |
| +221784567890    | 8888 | Orange Money | WO     | S5 USSD  |
