"""Drawdown routes - all drawdown endpoints, sparklines, monthly growth"""
from fastapi import APIRouter, Query, Path
from services import mt5_connector
from db import account_balance_history
from models import MonthlyDrawdown, DailyDrawdown, WeeklyDrawdown, YearlyDrawdown

router = APIRouter()


@router.get("/monthly-drawdown", response_model=list[MonthlyDrawdown])
async def get_monthly_drawdown():
    """Get monthly drawdown data"""
    return mt5_connector.get_monthly_drawdown()


@router.get("/daily-drawdown", response_model=list[DailyDrawdown])
async def get_daily_drawdown():
    """Get daily drawdown data"""
    return mt5_connector.get_daily_drawdown()


@router.get("/weekly-drawdown", response_model=list[WeeklyDrawdown])
async def get_weekly_drawdown():
    """Get weekly drawdown data"""
    return mt5_connector.get_weekly_drawdown()


@router.get("/yearly-drawdown", response_model=list[YearlyDrawdown])
async def get_yearly_drawdown():
    """Get yearly drawdown data"""
    return mt5_connector.get_yearly_drawdown()


@router.post("/reset-drawdown")
async def reset_drawdown():
    """Reset peak balance for drawdown calculation"""
    mt5_connector.reset_peak_balance()
    return {"message": "Reset done"}


@router.get("/sparklines")
async def get_all_sparklines(
    points: int = Query(default=20, ge=5, le=100, description="Nombre de points par sparkline")
):
    """Récupère les sparklines (historique balance) pour tous les comptes"""
    return account_balance_history.get_all_sparklines(points)


@router.get("/global-monthly-growth")
async def get_global_monthly_growth(
    refresh: bool = Query(default=False, description="Forcer le recalcul (ignorer le cache)")
):
    """Récupère la croissance mensuelle agrégée de tous les comptes (cache 24h)"""
    return mt5_connector.get_global_monthly_growth(use_cache=not refresh)


@router.get("/accounts/{account_id}/balance-history")
async def get_account_balance_history(
    account_id: int = Path(..., description="ID du compte MT5"),
    days: int = Query(default=30, ge=1, le=365, description="Nombre de jours d'historique")
):
    """Récupère l'historique des balances pour un compte spécifique"""
    history = account_balance_history.get_history(account_id, days)
    if not history:
        return []
    return history
