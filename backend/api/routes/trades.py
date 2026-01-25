"""Trades routes - trades history, positions, history points"""
from fastapi import APIRouter, Query
from services import mt5_connector
from models import Trade, Position, HistoryPoint

router = APIRouter()


@router.get("/trades", response_model=list[Trade])
async def get_trades(days: int = Query(default=30, ge=1, le=365)):
    """Get trade history for the specified number of days"""
    return mt5_connector.get_history_trades(days)


@router.get("/positions", response_model=list[Position])
async def get_positions():
    """Get open positions"""
    return mt5_connector.get_open_positions()


@router.get("/history", response_model=list[HistoryPoint])
async def get_history(limit: int = Query(default=60, ge=1, le=3600)):
    """Get balance/equity history points"""
    return mt5_connector.get_history(limit)
