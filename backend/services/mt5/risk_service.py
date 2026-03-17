"""MT5 Risk Service - Risk metrics, drawdown, Sharpe ratio"""
from models import RiskMetrics, DailyDrawdown
from .shared_state import MT5SharedState


class RiskService:
    def __init__(self, state: MT5SharedState, mt5):
        self.state = state
        self.mt5 = mt5

    def get_risk_metrics(self) -> RiskMetrics | None:
        state = self.state
        info = self.mt5.account_info()
        if not info:
            return None

        current_dd = max(0, state.peak_equity - info.equity)
        current_dd_pct = (current_dd / state.peak_equity * 100) if state.peak_equity > 0 else 0

        # Deposit load
        deposit_load = (info.margin / info.equity * 100) if info.equity > 0 else 0

        # Sharpe ratio (simplified)
        sharpe = 0.0
        if len(state.history) > 10:
            returns = []
            hist = list(state.history)
            for i in range(1, len(hist)):
                if hist[i-1].equity > 0:
                    r = (hist[i].equity - hist[i-1].equity) / hist[i-1].equity
                    returns.append(r)
            if returns:
                avg_return = sum(returns) / len(returns)
                std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
                sharpe = (avg_return / std_return) if std_return > 0 else 0

        # Recovery factor
        net_profit = info.balance - state.initial_deposit if state.initial_deposit > 0 else info.profit
        recovery = (net_profit / state.max_drawdown) if state.max_drawdown > 0 else 0

        return RiskMetrics(
            max_drawdown=state.max_drawdown,
            max_drawdown_percent=state.max_drawdown_percent,
            relative_drawdown_balance=state.max_drawdown_percent,
            relative_drawdown_equity=current_dd_pct,
            max_deposit_load=deposit_load,
            sharpe_ratio=round(sharpe, 2),
            recovery_factor=round(recovery, 2),
            current_drawdown=current_dd,
            current_drawdown_percent=current_dd_pct
        )

    def get_daily_drawdown(self) -> list[DailyDrawdown]:
        history = list(self.state.history)
        if not history:
            return []

        # Group by day
        daily_data: dict[str, list] = {}
        for point in history:
            day_key = point.timestamp.strftime('%Y-%m-%d')
            if day_key not in daily_data:
                daily_data[day_key] = []
            daily_data[day_key].append(point)

        result = []
        sorted_days = sorted(daily_data.keys())
        prev_day_end_balance = None

        for day in sorted_days:
            points = daily_data[day]
            start_balance = prev_day_end_balance if prev_day_end_balance else points[0].balance

            day_peak = start_balance
            day_min = start_balance
            for p in points:
                if p.balance > day_peak:
                    day_peak = p.balance
                if p.balance < day_min:
                    day_min = p.balance

            if day_peak > 0:
                dd_percent = max(0, (day_peak - day_min) / day_peak * 100)
            else:
                dd_percent = 0

            result.append(DailyDrawdown(
                date=day,
                drawdown_percent=round(dd_percent, 2),
                start_balance=round(start_balance, 2),
                min_balance=round(day_min, 2)
            ))

            prev_day_end_balance = points[-1].balance

        return result

    def reset_peak_balance(self):
        info = self.mt5.account_info()
        if info:
            self.state.peak_balance = info.balance
            self.state.peak_equity = info.equity
