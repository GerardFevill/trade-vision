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
    client: str | None = None


class PortefeuilleAccountDetail(BaseModel):
    """Account within a portfolio with its lot factor"""
    account_id: int
    lot_factor: float
    account: AccountSummary | None = None


class PortefeuilleSummary(BaseModel):
    """Summary of a portfolio for list views"""
    id: int
    name: str
    type: str
    client: str
    total_balance: float
    total_profit: float
    account_count: int
    created_at: str
    updated_at: str


class PortefeuilleDetail(BaseModel):
    """Detailed portfolio with accounts grouped by factor"""
    id: int
    name: str
    type: str
    client: str
    total_balance: float
    total_equity: float
    total_profit: float
    account_count: int
    accounts: list[PortefeuilleAccountDetail]
    available_factors: list[float]
    created_at: str
    updated_at: str


# Monthly records response models
class MonthlyAccountRecord(BaseModel):
    """Monthly record for one account"""
    account_id: int
    account_name: str
    lot_factor: float
    starting_balance: float
    ending_balance: float
    profit: float
    profit_percent: float
    weight: float  # Relative weight based on lot factor
    suggested_withdrawal: float
    actual_withdrawal: float
    currency: str


class MonthlySnapshot(BaseModel):
    """Monthly summary for a portfolio"""
    month: str  # YYYY-MM
    total_starting: float
    total_ending: float
    total_profit: float
    total_profit_percent: float
    total_withdrawal: float
    accounts: list[MonthlyAccountRecord]
    is_closed: bool  # True if withdrawals have been recorded


class MonthlyHistory(BaseModel):
    """Monthly history list for a portfolio"""
    portfolio_id: int
    portfolio_name: str
    months: list[MonthlySnapshot]
