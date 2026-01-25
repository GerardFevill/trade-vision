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


@router.post("/rebuild-all-sparklines")
async def rebuild_all_sparklines():
    """Reconstruit les sparklines depuis les deals MT5 pour tous les comptes"""
    import MetaTrader5 as mt5
    from datetime import datetime
    from config import MT5_ACCOUNTS, MT5_TERMINALS

    results = {}

    for acc_config in MT5_ACCOUNTS:
        account_id = acc_config["id"]
        terminal_key = acc_config.get("terminal", "roboforex")
        terminal_path = MT5_TERMINALS.get(terminal_key)

        try:
            # Se connecter au compte
            mt5.shutdown()
            init_params = {
                "login": acc_config["id"],
                "password": acc_config["password"],
                "server": acc_config["server"],
                "timeout": 60000
            }
            if terminal_path:
                init_params["path"] = terminal_path

            if not mt5.initialize(**init_params):
                results[account_id] = {"status": "error", "message": str(mt5.last_error())}
                continue

            # Récupérer les deals
            deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
            if not deals:
                results[account_id] = {"status": "no_deals", "points": 0}
                continue

            # Calculer la balance au fil du temps
            sorted_deals = sorted(deals, key=lambda d: d.time)
            running_balance = 0.0
            balance_points = []
            last_date = None

            for d in sorted_deals:
                deal_time = datetime.fromtimestamp(d.time)
                deal_date = deal_time.date()

                if d.type == mt5.DEAL_TYPE_BALANCE:
                    running_balance += d.profit
                elif d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
                    running_balance += d.profit + d.commission + d.swap

                # Un point par jour
                if last_date != deal_date and running_balance > 0:
                    balance_points.append((deal_time, running_balance))
                    last_date = deal_date

            # Sauvegarder dans account_balance_history
            points_saved = 0
            for ts, balance in balance_points:
                if account_balance_history.save_snapshot_at_time(account_id, balance, balance, ts):
                    points_saved += 1

            results[account_id] = {"status": "rebuilt", "points": points_saved}

        except Exception as e:
            results[account_id] = {"status": "error", "message": str(e)}

    return results
