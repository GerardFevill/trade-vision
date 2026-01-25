"""MT5 Bridge Service - Runs on Windows to provide MT5 access to Docker containers"""
import MetaTrader5 as mt5
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Any
import uvicorn

app = FastAPI(title="MT5 Bridge", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InitRequest(BaseModel):
    path: Optional[str] = None


class LoginRequest(BaseModel):
    login: int
    password: str
    server: str


class HistoryRequest(BaseModel):
    date_from: str
    date_to: str


def serialize_account_info(info) -> dict:
    if info is None:
        return None
    return {
        "login": info.login,
        "server": info.server,
        "balance": info.balance,
        "equity": info.equity,
        "margin": info.margin,
        "margin_free": info.margin_free,
        "margin_level": info.margin_level if info.margin_level else 0,
        "profit": info.profit,
        "currency": info.currency,
        "leverage": info.leverage,
        "name": info.name,
        "company": info.company,
    }


def serialize_position(pos) -> dict:
    return {
        "ticket": pos.ticket,
        "symbol": pos.symbol,
        "type": pos.type,
        "volume": pos.volume,
        "price_open": pos.price_open,
        "price_current": pos.price_current,
        "profit": pos.profit,
        "swap": pos.swap,
        "time": pos.time,
        "sl": pos.sl,
        "tp": pos.tp,
        "magic": pos.magic,
        "comment": pos.comment,
    }


def serialize_deal(deal) -> dict:
    return {
        "ticket": deal.ticket,
        "order": deal.order,
        "time": deal.time,
        "type": deal.type,
        "entry": deal.entry,
        "symbol": deal.symbol,
        "volume": deal.volume,
        "price": deal.price,
        "profit": deal.profit,
        "swap": deal.swap,
        "commission": deal.commission,
        "magic": deal.magic,
        "comment": deal.comment,
    }


@app.get("/health")
def health():
    return {"status": "ok", "mt5_connected": mt5.terminal_info() is not None}


@app.post("/initialize")
def initialize(request: InitRequest):
    if request.path:
        success = mt5.initialize(request.path)
    else:
        success = mt5.initialize()
    return {"success": success}


@app.post("/shutdown")
def shutdown():
    mt5.shutdown()
    return {"success": True}


@app.post("/login")
def login(request: LoginRequest):
    success = mt5.login(request.login, password=request.password, server=request.server)
    return {"success": success}


@app.get("/account_info")
def account_info():
    info = mt5.account_info()
    return serialize_account_info(info)


@app.get("/positions")
def positions():
    positions = mt5.positions_get()
    if positions is None:
        return []
    return [serialize_position(p) for p in positions]


@app.post("/history_deals")
def history_deals(request: HistoryRequest):
    date_from = datetime.fromisoformat(request.date_from)
    date_to = datetime.fromisoformat(request.date_to)
    deals = mt5.history_deals_get(date_from, date_to)
    if deals is None:
        return []
    return [serialize_deal(d) for d in deals]


@app.get("/last_error")
def last_error():
    error = mt5.last_error()
    return {"code": error[0], "message": error[1]}


@app.get("/terminal_info")
def terminal_info():
    info = mt5.terminal_info()
    if info is None:
        return None
    return {
        "connected": info.connected,
        "path": info.path,
        "data_path": info.data_path,
        "company": info.company,
        "name": info.name,
    }


if __name__ == "__main__":
    print("Starting MT5 Bridge on port 8001...")
    print("This service provides MT5 access to Docker containers")
    uvicorn.run(app, host="0.0.0.0", port=8001)
