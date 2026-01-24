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


class ConnectionStatus(BaseModel):
    connected: bool
    server: str | None
    account: int | None
    name: str | None
    company: str | None


class MonthlyGrowth(BaseModel):
    year: int
    months: dict[str, float | None]  # Jan -> Dec percentages
    values: dict[str, float | None]  # Jan -> Dec profit values
    year_total: float | None
    year_total_value: float | None


class MonthlyDrawdown(BaseModel):
    year: int
    months: dict[str, float | None]  # Jan -> Dec max drawdown %
    year_max: float | None  # Max drawdown of the year


class DailyDrawdown(BaseModel):
    date: str  # YYYY-MM-DD
    drawdown_percent: float
    start_balance: float
    min_balance: float


class WeeklyDrawdown(BaseModel):
    year: int
    week: int  # Week number 1-52
    start_date: str
    drawdown_percent: float


class YearlyDrawdown(BaseModel):
    year: int
    drawdown_percent: float
    start_balance: float
    min_balance: float


class FullDashboard(BaseModel):
    account: AccountInfo
    stats: AccountStats
    trade_stats: TradeStats
    risk_metrics: RiskMetrics
    open_positions: list[Position]
    monthly_growth: list[MonthlyGrowth]
