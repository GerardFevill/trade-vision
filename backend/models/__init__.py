"""Models module - Pydantic schemas"""
from .domain import (
    AccountInfo, AccountStats, TradeStats, RiskMetrics,
    Trade, Position, HistoryPoint, MonthlyGrowth, DailyDrawdown,
    LOT_FACTORS, PORTFOLIO_TYPES, Portefeuille, PortefeuilleAccount,
    PortefeuilleMonthlyRecord
)
from .responses import (
    ConnectionStatus, FullDashboard, AccountSummary,
    PortefeuilleSummary, PortefeuilleDetail, PortefeuilleAccountDetail,
    MonthlyAccountRecord, MonthlySnapshot, MonthlyHistory
)

__all__ = [
    # Domain models
    'AccountInfo', 'AccountStats', 'TradeStats', 'RiskMetrics',
    'Trade', 'Position', 'HistoryPoint', 'MonthlyGrowth', 'DailyDrawdown',
    # Portfolio models
    'LOT_FACTORS', 'PORTFOLIO_TYPES', 'Portefeuille', 'PortefeuilleAccount',
    'PortefeuilleMonthlyRecord',
    # Response models
    'ConnectionStatus', 'FullDashboard', 'AccountSummary',
    'PortefeuilleSummary', 'PortefeuilleDetail', 'PortefeuilleAccountDetail',
    'MonthlyAccountRecord', 'MonthlySnapshot', 'MonthlyHistory',
]
