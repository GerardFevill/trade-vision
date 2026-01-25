"""Response models - API response schemas"""
from pydantic import BaseModel
from .domain import AccountInfo, AccountStats, TradeStats, RiskMetrics, Position, MonthlyGrowth


class ConnectionStatus(BaseModel):
    connected: bool
    server: str | None
    account: int | None
    name: str | None
    company: str | None


class FullDashboard(BaseModel):
    account: AccountInfo
    stats: AccountStats
    trade_stats: TradeStats
    risk_metrics: RiskMetrics
    open_positions: list[Position]
    monthly_growth: list[MonthlyGrowth]


class AccountSummary(BaseModel):
    """Résumé d'un compte pour la liste des comptes"""
    id: int
    name: str
    broker: str
    server: str
    balance: float
    equity: float
    profit: float
    profit_percent: float
    drawdown: float
    trades: int
    win_rate: float
    currency: str
    leverage: int
    connected: bool
