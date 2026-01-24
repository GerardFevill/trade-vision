from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from mt5_connector import mt5_connector
from models import (
    AccountInfo, AccountStats, TradeStats, RiskMetrics,
    Trade, Position, HistoryPoint, ConnectionStatus, FullDashboard, MonthlyDrawdown,
    DailyDrawdown, WeeklyDrawdown, YearlyDrawdown
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    mt5_connector.connect()
    yield
    mt5_connector.disconnect()


app = FastAPI(title="MT5 Monitor API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/status", response_model=ConnectionStatus)
async def get_status():
    return mt5_connector.get_connection_status()


@app.get("/api/account", response_model=AccountInfo)
async def get_account():
    data = mt5_connector.get_account_info()
    if not data:
        raise HTTPException(503, "MT5 unavailable")
    return data


@app.get("/api/stats", response_model=AccountStats)
async def get_stats():
    data = mt5_connector.get_account_stats()
    if not data:
        raise HTTPException(503, "MT5 unavailable")
    return data


@app.get("/api/trade-stats", response_model=TradeStats)
async def get_trade_stats():
    data = mt5_connector.get_trade_stats()
    if not data:
        raise HTTPException(503, "MT5 unavailable")
    return data


@app.get("/api/risk", response_model=RiskMetrics)
async def get_risk():
    data = mt5_connector.get_risk_metrics()
    if not data:
        raise HTTPException(503, "MT5 unavailable")
    return data


@app.get("/api/trades", response_model=list[Trade])
async def get_trades(days: int = Query(default=30, ge=1, le=365)):
    return mt5_connector.get_history_trades(days)


@app.get("/api/positions", response_model=list[Position])
async def get_positions():
    return mt5_connector.get_open_positions()


@app.get("/api/history", response_model=list[HistoryPoint])
async def get_history(limit: int = Query(default=60, ge=1, le=3600)):
    return mt5_connector.get_history(limit)


@app.get("/api/dashboard", response_model=FullDashboard)
async def get_dashboard():
    data = mt5_connector.get_full_dashboard()
    if not data:
        raise HTTPException(503, "MT5 unavailable")
    return data


@app.get("/api/monthly-drawdown", response_model=list[MonthlyDrawdown])
async def get_monthly_drawdown():
    return mt5_connector.get_monthly_drawdown()


@app.get("/api/daily-drawdown", response_model=list[DailyDrawdown])
async def get_daily_drawdown():
    return mt5_connector.get_daily_drawdown()


@app.get("/api/weekly-drawdown", response_model=list[WeeklyDrawdown])
async def get_weekly_drawdown():
    return mt5_connector.get_weekly_drawdown()


@app.get("/api/yearly-drawdown", response_model=list[YearlyDrawdown])
async def get_yearly_drawdown():
    return mt5_connector.get_yearly_drawdown()


@app.post("/api/reset-drawdown")
async def reset_drawdown():
    mt5_connector.reset_peak_balance()
    return {"message": "Reset done"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
