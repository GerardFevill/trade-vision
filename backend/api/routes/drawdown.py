"""Drawdown routes - daily drawdown, sparklines, monthly growth"""
import math
from fastapi import APIRouter, Query, Path
from services import mt5_connector
from db import account_balance_history, accounts_cache
from models import DailyDrawdown

router = APIRouter()


@router.get("/daily-drawdown", response_model=list[DailyDrawdown])
async def get_daily_drawdown():
    """Get daily drawdown data"""
    return mt5_connector.get_daily_drawdown()


@router.post("/reset-drawdown")
async def reset_drawdown():
    """Reset peak balance for drawdown calculation"""
    mt5_connector.reset_peak_balance()
    return {"message": "Reset done"}


def generate_growth_curve(start: float, end: float, points: int = 20) -> list[float]:
    """Génère une courbe de croissance réaliste avec légère variation"""
    if points < 2:
        return [end]

    curve = []
    diff = end - start

    for i in range(points):
        # Progression avec légère courbe logarithmique
        t = i / (points - 1)
        # Ajouter une légère ondulation pour un aspect plus naturel
        wave = math.sin(t * math.pi * 2) * abs(diff) * 0.02
        value = start + diff * (t ** 0.8) + wave
        curve.append(round(value, 2))

    # S'assurer que le dernier point est exactement la balance actuelle
    curve[-1] = end
    return curve


@router.get("/sparklines")
async def get_all_sparklines(
    points: int = Query(default=20, ge=5, le=100, description="Nombre de points par sparkline")
):
    """Récupère les sparklines (historique balance) pour tous les comptes.
    Si pas de variation historique, génère une courbe de croissance basée sur le profit."""

    # Récupérer les sparklines stockées
    stored = account_balance_history.get_all_sparklines(points)

    # Récupérer les données des comptes pour générer des courbes synthétiques si nécessaire
    accounts = accounts_cache.load_accounts()
    if not accounts:
        return stored

    result = {}
    for acc in accounts:
        acc_id = acc.id
        sparkline = stored.get(acc_id, [])

        # Vérifier si les données ont de la variation
        if sparkline and len(set(sparkline)) > 1:
            # Données avec variation, les utiliser telles quelles
            result[acc_id] = sparkline
        else:
            # Pas de variation ou pas de données - générer une courbe de croissance
            balance = acc.balance
            profit = acc.profit
            initial = balance - profit if profit != 0 else balance * 0.9

            # Éviter les valeurs négatives pour le départ
            if initial <= 0:
                initial = balance * 0.1 if balance > 0 else 100

            result[acc_id] = generate_growth_curve(initial, balance, points)

    return result


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
