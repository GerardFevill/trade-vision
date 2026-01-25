"""Analytics routes - stats, trade stats, risk metrics"""
from fastapi import APIRouter, HTTPException
from services import mt5_connector
from models import AccountStats, TradeStats, RiskMetrics

router = APIRouter()


@router.get("/stats", response_model=AccountStats)
async def get_stats():
    """Get account statistics"""
    data = mt5_connector.get_account_stats()
    if not data:
        raise HTTPException(503, "MT5 unavailable")
    return data


@router.get("/trade-stats", response_model=TradeStats)
async def get_trade_stats():
    """Get trading statistics"""
    data = mt5_connector.get_trade_stats()
    if not data:
        raise HTTPException(503, "MT5 unavailable")
    return data


@router.get("/risk", response_model=RiskMetrics)
async def get_risk():
    """Get risk metrics"""
    data = mt5_connector.get_risk_metrics()
    if not data:
        raise HTTPException(503, "MT5 unavailable")
    return data
