"""Domain models - Core business entities"""
from pydantic import BaseModel
from datetime import datetime


class AccountInfo(BaseModel):
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float | None
    profit: float
    leverage: int
    server: str
    name: str
    login: int
    currency: str
    trade_mode: str


class AccountStats(BaseModel):
    balance: float
    equity: float
    profit: float
    drawdown: float
    drawdown_percent: float
    initial_deposit: float
    total_deposits: float
    total_withdrawals: float
    growth_percent: float
    timestamp: datetime


class TradeStats(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    best_trade: float
    worst_trade: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    average_profit: float
    average_loss: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    longs_count: int
    shorts_count: int
    longs_won: int
    shorts_won: int
    avg_holding_time_seconds: float
    expected_payoff: float


class RiskMetrics(BaseModel):
    max_drawdown: float
    max_drawdown_percent: float
    relative_drawdown_balance: float
    relative_drawdown_equity: float
    max_deposit_load: float
    sharpe_ratio: float
    recovery_factor: float
    current_drawdown: float
    current_drawdown_percent: float


class Trade(BaseModel):
    ticket: int
    symbol: str
    type: str
    volume: float
    open_time: datetime
    open_price: float
    close_time: datetime | None
    close_price: float | None
    profit: float
    commission: float
    swap: float
    comment: str


class Position(BaseModel):
    ticket: int
    symbol: str
    type: str
    volume: float
    open_time: datetime
    open_price: float
    current_price: float
    profit: float
    sl: float | None
    tp: float | None


class HistoryPoint(BaseModel):
    balance: float
    equity: float
    drawdown: float
    drawdown_percent: float
    timestamp: datetime


class MonthlyGrowth(BaseModel):
    year: int
    months: dict[str, float | None]  # Jan -> Dec percentages
    values: dict[str, float | None]  # Jan -> Dec profit values
    year_total: float | None
    year_total_value: float | None


class DailyDrawdown(BaseModel):
    date: str  # YYYY-MM-DD
    drawdown_percent: float
    start_balance: float
    min_balance: float


# Portfolio management
LOT_FACTORS = [0.2, 0.6, 1.0, 1.4, 1.8, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]

PORTFOLIO_TYPES = {
    "Securise": [],  # Pas de facteur - nombre illimite de comptes
    "Conservateur": [0.2, 0.6, 1.0, 1.4, 1.8],
    "Modere": [2.0],
    "Agressif": [2.5, 3.0, 3.5, 4.0, 4.5],
}


class Portefeuille(BaseModel):
    id: int
    name: str  # "Conservateur", "Modere", "Agressif" or custom name
    type: str  # "Conservateur", "Modere", "Agressif"
    client: str  # "Akaj", "CosmosElite"
    created_at: datetime
    updated_at: datetime


class PortefeuilleAccount(BaseModel):
    portfolio_id: int
    account_id: int
    lot_factor: float  # 0.2 -> 4.5


class PortefeuilleMonthlyRecord(BaseModel):
    """Monthly snapshot for a portfolio account"""
    id: int
    portfolio_id: int
    account_id: int
    month: str  # YYYY-MM format
    lot_factor: float
    starting_balance: float
    ending_balance: float
    profit: float
    withdrawal: float
    note: str | None
    created_at: datetime


class PortefeuilleMonthlySnapshot(BaseModel):
    """Monthly summary for entire portfolio"""
    month: str  # YYYY-MM
    total_starting: float
    total_ending: float
    total_profit: float
    total_withdrawal: float
    accounts: list["PortefeuilleAccountMonthly"]


class PortefeuilleAccountMonthly(BaseModel):
    """Monthly data for one account in portfolio"""
    account_id: int
    account_name: str
    lot_factor: float
    starting_balance: float
    ending_balance: float
    profit: float
    profit_percent: float
    suggested_withdrawal: float  # Based on lot factor distribution
    actual_withdrawal: float
    currency: str
