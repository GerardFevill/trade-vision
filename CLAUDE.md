# Trade Vision — MT5 Monitor

## Projet
Dashboard de monitoring temps réel pour comptes de trading MetaTrader 5 et cTrader.
Multi-comptes, analytics, gestion de portefeuilles, suivi des drawdowns.

## Version
1.2.0 (fichier VERSION à la racine)

## Stack technique
- **Frontend** : Angular 21 + TypeScript 5.9 + SCSS + Chart.js
- **Backend** : FastAPI (Python 3.11) + Pydantic 2
- **Base de données** : PostgreSQL 16
- **Infra** : Docker Compose, GitHub Actions, Docker Hub (amesika2)
- **Bridge MT5** : Service Windows FastAPI sur port 8001

## Structure du projet
```
mt5-monitor/
├── backend/           # API FastAPI
│   ├── api/routes/    # Endpoints REST
│   ├── services/      # Logique métier (MT5, cTrader, sync)
│   ├── models/        # Modèles Pydantic
│   ├── config/        # Configuration (settings, accounts)
│   ├── db/            # Connexion PostgreSQL + repositories
│   └── scripts/       # Scripts utilitaires
├── frontend/          # App Angular
│   └── src/app/
│       ├── features/  # accounts, account-detail, portfolios
│       ├── data-access/ # Services API + modèles TS
│       ├── core/      # Services transversaux
│       └── shared/    # Composants réutilisables (badge, sparkline, stat-card)
├── mt5-bridge/        # Bridge Windows MT5 (port 8001)
├── .github/workflows/ # CI/CD (backend.yml, frontend.yml, release.yml)
├── docs/              # Documentation projet
└── docker-compose.yml # Orchestration des services
```

## Ports
| Service   | Dev         | Docker      |
|-----------|-------------|-------------|
| Frontend  | 4200        | 10003:80    |
| Backend   | 8000        | 10004:8000  |
| MT5 Bridge| 8001        | N/A (host)  |
| PostgreSQL| 5432        | 10005:5432  |

## Commandes de développement

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
ng serve  # ou npm start
```

### Docker
```bash
docker-compose up -d
```

## Architecture backend
- **MT5Connector** (`mt5_service.py`) : Connecteur principal MT5
- **CTraderConnector** (`ctrader_service.py`) : Connecteur cTrader
- **MT5BridgeClient** (`mt5_bridge_client.py`) : Client HTTP vers le bridge Windows
- **SyncService** (`sync_service.py`) : Synchronisation données

## Endpoints API principaux
- `GET /api/accounts` — Liste des comptes (MT5 + cTrader)
- `POST /api/accounts/{id}/connect` — Connexion à un compte
- `GET /api/dashboard` — Données dashboard
- `GET /api/analytics` — Statistiques de trading
- `GET /api/trades` — Historique des trades
- `GET /api/drawdown` — Métriques de drawdown
- `GET /api/portefeuilles` — Gestion des portefeuilles
- `GET /api/alerts` — Alertes
- `GET /api/export` — Export Excel

## Git
- Remote : https://github.com/gerardfevill/trade-vision.git
- Branch principale : master
- Ne JAMAIS ajouter "Co-Authored-By: Claude" dans les commits
- Ne pas mentionner Claude Code dans les messages de commit ou PR

## Docker Hub
- Registry : docker.io/amesika2
- Images :
  - `amesika2/trade-vision-frontend:v{VERSION}`
  - `amesika2/trade-vision-backend:v{VERSION}`

## Fichiers sensibles (ne jamais committer)
- `backend/.env` — Variables d'environnement
- `backend/config/accounts_local.py` — Comptes MT5 locaux
- `backend/config/ctrader_accounts_local.py` — Comptes cTrader locaux

## Conventions
- Commits : Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`)
- Backend : snake_case, type hints, Pydantic models
- Frontend : camelCase, standalone components Angular, feature-based structure
- Styles : SCSS avec variables globales
