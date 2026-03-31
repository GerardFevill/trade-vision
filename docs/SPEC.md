# Elite Monitor - Specification

## Overview

Elite Monitor is a multi-platform trading account monitoring application. It aggregates data from multiple trading platforms (MetaTrader 5 and cTrader) into a unified dashboard for portfolio tracking, performance analysis, and risk management.

## Architecture

### Stack

- **Frontend**: Angular 19 + TypeScript (standalone components, signals)
- **Backend**: Python FastAPI + Uvicorn
- **Database**: PostgreSQL
- **Deployment**: Docker Compose

### Structure

```
frontend/          Angular 19 SPA
backend/
  api/routes/      FastAPI route modules
  services/        Platform connectors (MT5, cTrader)
  models/          Pydantic response models
  db/              PostgreSQL repositories
  config/          Account configs, logging
```

## Supported Platforms

### MetaTrader 5 (MT5)

- Direct connection via `MetaTrader5` Python package
- Multiple terminals supported (RoboForex, IC Markets, Deriv)
- Full trade history, open positions, account stats
- Bridge mode available for Docker deployment

### cTrader

- Connection via cTrader Open API (Protobuf over TCP/TLS)
- OAuth2 authentication (client_id, client_secret, access_token)
- Endpoint: `live.ctraderapi.com:5035`
- Account discovery via `getAccountListByAccessToken`
- Balance, equity, positions via Protobuf messages

### Unified Model

Both platforms return `AccountSummary` with identical fields:
- `id`, `name`, `broker`, `server`
- `balance`, `equity`, `profit`, `profit_percent`
- `drawdown`, `trades`, `win_rate`
- `currency`, `leverage`, `connected`
- `client` (optional, for client filtering)
- `copy_invested`, `copy_strategy` (optional, cTrader copy trading)

## Key Features

### Account Monitoring

- Real-time balance/equity tracking
- Grid and table view with sorting and filtering
- Client-based filtering (Fevill, Akaj, Vitogbe)
- Sparkline charts for balance evolution
- Favorites system (local storage)

### Copy Trading Detection (cTrader)

cTrader accounts invested in copy strategies show $0 free balance because funds are transferred to internal copy accounts. Elite Monitor detects copy investments via cash flow history:

- Scans `CashFlowHistory` in 7-day windows from account registration
- `operationType 30` = copy investment (delta negative)
- `operationType 33` = copy withdrawal (delta positive)
- Extracts strategy name from `externalNote` via regex
- Computes effective balance = free balance + net copy invested
- Displays copy badge on account cards

### Portfolio Management

Four portfolio types with distinct rules:

| Type | Lot Factors | Profit Withdrawal | Distribution |
|------|-------------|-------------------|--------------|
| Securise | N/A | 50% | Simple |
| Conservateur | 0.2 - 1.8 (5 levels) | Elite system | Elite (5 capital phases) |
| Modere | 2.0 | 80% | Simple |
| Agressif | 2.5 - 4.5 | 90% | Simple |

Monthly snapshots with auto-closing and balance history tracking.

### Analytics

- Trade statistics (win rate, profit factor, best/worst trade)
- Risk metrics (Sharpe ratio, max drawdown, recovery factor)
- Monthly growth table (% and absolute values)
- Radar chart performance visualization
- Balance/equity history charts

### Alerts

- Configurable alert conditions per account
- Types: balance, equity, drawdown, margin level
- Status tracking: active, triggered, disabled
- Alert history log

### Export

- CSV and Excel export for trades, accounts, history
- Rate limited (10 requests/minute)

## API Endpoints

### Accounts (`/api/accounts/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/accounts` | List all accounts (MT5 + cTrader, cached) |
| GET | `/accounts?force_mt5=true` | Force live sync from platforms |
| POST | `/accounts/{id}/connect` | Connect to specific account |
| POST | `/accounts/{id}/reset-peaks` | Reset drawdown peaks |
| POST | `/sync/all` | Background sync all accounts |

### Dashboard (`/api/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard` | Full dashboard data |
| GET | `/stats` | Account statistics |
| GET | `/trade-stats` | Trading statistics |
| GET | `/risk` | Risk metrics |
| GET | `/positions` | Open positions |
| GET | `/trades` | Trade history |
| GET | `/sparklines` | Growth sparklines for all accounts |

### Portfolios (`/api/portefeuilles/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/portefeuilles` | List portfolios |
| POST | `/portefeuilles` | Create portfolio |
| GET | `/portefeuilles/{id}` | Portfolio detail |
| GET | `/portefeuilles/{id}/monthly/{month}` | Monthly snapshot |
| POST | `/portefeuilles/{id}/monthly-current/close` | Close current month |

### Alerts (`/api/alerts/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/alerts` | List alerts |
| POST | `/alerts` | Create alert |
| PUT | `/alerts/{id}` | Update alert |
| DELETE | `/alerts/{id}` | Delete alert |

### Export (`/api/export/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/export/trades/csv` | Export trades as CSV |
| GET | `/export/trades/excel` | Export trades as Excel |
| GET | `/export/accounts/csv` | Export accounts as CSV |
| GET | `/export/accounts/excel` | Export accounts as Excel |

## Configuration

### Environment Variables

```
POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
MT5_MODE=bridge|direct
MT5_BRIDGE_URL=http://localhost:8001
CTRADER_CLIENT_ID, CTRADER_CLIENT_SECRET
CTRADER_ACCESS_TOKEN, CTRADER_REFRESH_TOKEN
CTRADER_HOST, CTRADER_PORT
```

### Account Configuration

- MT5: `backend/config/accounts_local.py` (list of account dicts with id, password, server, name, terminal, broker, client)
- cTrader: `backend/config/ctrader_accounts_local.py` (credentials + account list)
- Clients/Profiles: `Fevill`, `Akaj`, `Vitogbe`
- Brokers supportés: RoboForex, IC Markets, Deriv (SVG) LLC, Fusion Markets

## Running Locally

```bash
# Database (Docker)
docker compose up -d postgres

# Backend
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
ng serve --port 4200
```

## Deployment

```bash
docker compose up -d
```

Services: PostgreSQL (port 5432), Backend (port 8000), Frontend (port 80)
