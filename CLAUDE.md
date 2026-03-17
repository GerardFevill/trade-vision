# Elite Monitor - Contexte Projet

## Description
Application de monitoring multi-broker (MetaTrader 5 + cTrader) pour le suivi en temps réel de comptes de trading : performances, drawdown, portefeuilles, alertes.

## Architecture

```
frontend/    Angular 19 (standalone components, signals, Chart.js)
backend/     FastAPI + Python 3.11 (Pydantic, PostgreSQL, Protobuf)
mt5-bridge/  FastAPI Windows-only (pont HTTP vers terminal MT5)
docs/        Spécification (SPEC.md)
```

## Stack

| Couche     | Techno                        |
|------------|-------------------------------|
| Frontend   | Angular 19, TypeScript, SCSS  |
| Backend    | FastAPI, Python 3.11          |
| Database   | PostgreSQL 16                 |
| MT5        | MetaTrader5 Python + Bridge   |
| cTrader    | Protobuf over TCP/TLS         |
| Deploy     | Docker Compose                |
| Registry   | docker.io/amesika2            |
| Git        | github.com/gerardfevill/elite-monitor |

## Conventions de code

### Backend (Python)
- Pydantic v2 pour la validation
- Repositories dans `db/repositories/`
- Routes dans `api/routes/`
- Services métier dans `services/`
- Config via `pydantic-settings` + `.env`
- Logging : `loguru` + `structlog`

### Frontend (Angular)
- Standalone components uniquement (pas de NgModules)
- Signals pour la réactivité (pas de BehaviorSubject)
- Structure : `features/` > `pages/` + `ui/` + `data-access/`
- Theme sombre (#0a0a0a), accent bleu (#2962ff)
- FontAwesome pour les icônes

## Commandes utiles

```bash
# Backend (dev local)
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (dev local)
cd frontend && ng serve --port 4200

# MT5 Bridge (Windows uniquement)
cd mt5-bridge && python main.py

# Docker Compose (prod)
docker compose up -d

# PostgreSQL seul
docker compose up -d postgres
```

## Ports

| Service    | Dev    | Docker  |
|------------|--------|---------|
| Frontend   | 4200   | 10003   |
| Backend    | 8000   | 10004   |
| PostgreSQL | 5432   | 10005   |
| MT5 Bridge | 8001   | —       |

## Fichiers importants

- `backend/services/mt5_service.py` — Connecteur MT5 principal (~1200 lignes)
- `backend/services/ctrader_service.py` — Connecteur cTrader + copy trading
- `backend/config/settings.py` — Configuration centralisée
- `backend/config/accounts_local.py` — Comptes MT5 (non versionné)
- `backend/config/ctrader_accounts_local.py` — Comptes cTrader (non versionné)
- `frontend/src/app/data-access/api/mt5-api.service.ts` — Service API frontend

## Modèle unifié AccountSummary

Champs communs MT5 + cTrader :
`id, name, broker, server, balance, equity, profit, profit_percent, drawdown, trades, win_rate, currency, leverage, connected, client`
Champs cTrader spécifiques : `copy_invested, copy_strategy`

## Règles

- Ne JAMAIS lire ni afficher le contenu des fichiers `.env` ou `*_local.py`
- Ne JAMAIS committer de credentials
- Les images Docker s'appellent `amesika2/elite-monitor-*`
- Conventional Commits obligatoires
- Pas de signature IA dans les commits
