"""Analytics routes - stats, trade stats, risk metrics (from DB)"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from services import mt5_connector
from db import account_stats_repo
from models import AccountStats, TradeStats, RiskMetrics

router = APIRouter()


@router.get("/stats", response_model=AccountStats)
async def get_stats(live: bool = Query(default=False, description="Forcer données live MT5")):
    """Get account statistics (from DB, or live if requested)"""
    account_id = mt5_connector.current_account_id

    # Essayer depuis la DB d'abord
    if not live and account_id:
        db_stats = account_stats_repo.get_account_stats(account_id)
        if db_stats:
            return AccountStats(
                balance=db_stats['balance'] or 0,
                equity=db_stats['equity'] or 0,
                profit=db_stats['profit'] or 0,
                drawdown=db_stats['drawdown'] or 0,
                drawdown_percent=db_stats['drawdown_percent'] or 0,
                initial_deposit=db_stats['initial_deposit'] or 0,
                total_deposits=db_stats['total_deposits'] or 0,
                total_withdrawals=db_stats['total_withdrawals'] or 0,
                growth_percent=db_stats['growth_percent'] or 0,
                timestamp=db_stats['updated_at'] or datetime.now()
            )

    # Fallback sur MT5 live
    data = mt5_connector.get_account_stats()
    if not data:
        raise HTTPException(503, "MT5 unavailable and no cached data")
    return data


@router.get("/trade-stats", response_model=TradeStats)
async def get_trade_stats(live: bool = Query(default=False, description="Forcer données live MT5")):
    """Get trading statistics (from DB, or live if requested)"""
    account_id = mt5_connector.current_account_id

    # Essayer depuis la DB d'abord
    if not live and account_id:
        db_stats = account_stats_repo.get_trade_stats(account_id)
        if db_stats:
            return TradeStats(
                total_trades=db_stats['total_trades'] or 0,
                winning_trades=db_stats['winning_trades'] or 0,
                losing_trades=db_stats['losing_trades'] or 0,
                win_rate=db_stats['win_rate'] or 0,
                best_trade=db_stats['best_trade'] or 0,
                worst_trade=db_stats['worst_trade'] or 0,
                gross_profit=db_stats['gross_profit'] or 0,
                gross_loss=db_stats['gross_loss'] or 0,
                profit_factor=db_stats['profit_factor'] or 0,
                average_profit=db_stats['average_profit'] or 0,
                average_loss=db_stats['average_loss'] or 0,
                max_consecutive_wins=db_stats['max_consecutive_wins'] or 0,
                max_consecutive_losses=db_stats['max_consecutive_losses'] or 0,
                longs_count=db_stats['longs_count'] or 0,
                shorts_count=db_stats['shorts_count'] or 0,
                longs_won=db_stats['longs_won'] or 0,
                shorts_won=db_stats['shorts_won'] or 0,
                avg_holding_time_seconds=db_stats['avg_holding_time_seconds'] or 0,
                expected_payoff=db_stats['expected_payoff'] or 0
            )

    # Fallback sur MT5 live
    data = mt5_connector.get_trade_stats()
    if not data:
        raise HTTPException(503, "MT5 unavailable and no cached data")
    return data


@router.get("/risk", response_model=RiskMetrics)
async def get_risk(live: bool = Query(default=False, description="Forcer données live MT5")):
    """Get risk metrics (from DB, or live if requested)"""
    account_id = mt5_connector.current_account_id

    # Essayer depuis la DB d'abord
    if not live and account_id:
        db_metrics = account_stats_repo.get_risk_metrics(account_id)
        if db_metrics:
            return RiskMetrics(
                max_drawdown=db_metrics['max_drawdown'] or 0,
                max_drawdown_percent=db_metrics['max_drawdown_percent'] or 0,
                relative_drawdown_balance=db_metrics['relative_drawdown_balance'] or 0,
                relative_drawdown_equity=db_metrics['relative_drawdown_equity'] or 0,
                max_deposit_load=db_metrics['max_deposit_load'] or 0,
                sharpe_ratio=db_metrics['sharpe_ratio'] or 0,
                recovery_factor=db_metrics['recovery_factor'] or 0,
                current_drawdown=db_metrics['current_drawdown'] or 0,
                current_drawdown_percent=db_metrics['current_drawdown_percent'] or 0
            )

    # Fallback sur MT5 live
    data = mt5_connector.get_risk_metrics()
    if not data:
        raise HTTPException(503, "MT5 unavailable and no cached data")
    return data
