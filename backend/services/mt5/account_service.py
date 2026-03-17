"""MT5 Account Service - Account info, stats, and monthly profit"""
from datetime import datetime
from models import AccountInfo, AccountStats, HistoryPoint
from db import history_db
from .shared_state import MT5SharedState


class AccountService:
    def __init__(self, state: MT5SharedState, mt5):
        self.state = state
        self.mt5 = mt5

    def get_account_info(self) -> AccountInfo | None:
        info = self.mt5.account_info()
        if not info:
            return None

        trade_modes = {0: "Demo", 1: "Contest", 2: "Real"}

        return AccountInfo(
            balance=info.balance,
            equity=info.equity,
            margin=info.margin,
            free_margin=info.margin_free,
            margin_level=info.margin_level if info.margin_level else None,
            profit=info.profit,
            leverage=info.leverage,
            server=info.server,
            name=info.name,
            login=info.login,
            currency=info.currency,
            trade_mode=trade_modes.get(getattr(info, 'trade_mode', 2), "Unknown")
        )

    def get_account_stats(self) -> AccountStats | None:
        mt5 = self.mt5
        state = self.state

        info = mt5.account_info()
        if not info:
            return None

        if info.balance > state.peak_balance:
            state.peak_balance = info.balance
        if info.equity > state.peak_equity:
            state.peak_equity = info.equity

        drawdown = max(0, state.peak_equity - info.equity)
        drawdown_pct = (drawdown / state.peak_equity * 100) if state.peak_equity > 0 else 0

        if drawdown > state.max_drawdown:
            state.max_drawdown = drawdown
        if drawdown_pct > state.max_drawdown_percent:
            state.max_drawdown_percent = drawdown_pct

        # Calculate deposits/withdrawals
        deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
        total_deposits = 0.0
        total_withdrawals = 0.0
        if deals:
            for d in deals:
                if d.type == mt5.DEAL_TYPE_BALANCE:
                    if d.profit > 0:
                        total_deposits += d.profit
                    else:
                        total_withdrawals += abs(d.profit)

        if state.initial_deposit == 0 and total_deposits > 0:
            state.initial_deposit = total_deposits

        net_deposit = total_deposits - total_withdrawals
        total_profit = info.balance - net_deposit if net_deposit > 0 else 0

        growth = (total_profit / net_deposit * 100) if net_deposit > 0 else 0

        # Store history point
        now = datetime.now()
        point = HistoryPoint(
            balance=info.balance,
            equity=info.equity,
            drawdown=drawdown,
            drawdown_percent=drawdown_pct,
            timestamp=now
        )
        state.history.append(point)
        if state.current_account_id:
            history_db.save_point(point, state.current_account_id)

        return AccountStats(
            balance=info.balance,
            equity=info.equity,
            profit=total_profit,
            drawdown=drawdown,
            drawdown_percent=drawdown_pct,
            initial_deposit=state.initial_deposit,
            total_deposits=total_deposits,
            total_withdrawals=total_withdrawals,
            growth_percent=growth,
            timestamp=now
        )

    def get_current_month_profit(self) -> dict | None:
        mt5 = self.mt5

        info = mt5.account_info()
        if not info:
            return None

        current_balance = info.balance
        deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
        if not deals:
            return {"starting_balance": current_balance, "profit": 0.0, "current_balance": current_balance, "deposits": 0.0, "withdrawals": 0.0}

        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1)
        start_timestamp = start_of_month.timestamp()

        balance_start_of_month = 0.0
        deposits_this_month = 0.0
        withdrawals_this_month = 0.0

        for d in sorted(deals, key=lambda x: x.time):
            if d.time < start_timestamp:
                if d.type == mt5.DEAL_TYPE_BALANCE:
                    balance_start_of_month += d.profit
                elif d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
                    balance_start_of_month += d.profit + d.commission + d.swap
            else:
                if d.type == mt5.DEAL_TYPE_BALANCE:
                    if d.profit > 0:
                        deposits_this_month += d.profit
                    else:
                        withdrawals_this_month += abs(d.profit)

        effective_starting = balance_start_of_month + deposits_this_month - withdrawals_this_month
        trading_profit = current_balance - effective_starting

        return {
            "starting_balance": round(effective_starting, 2),
            "profit": round(trading_profit, 2),
            "current_balance": round(current_balance, 2),
            "deposits": round(deposits_this_month, 2),
            "withdrawals": round(withdrawals_this_month, 2)
        }

    def _calculate_monthly_growth(self, deals, current_balance: float) -> float:
        mt5 = self.mt5

        if not deals:
            return 0.0

        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1)
        start_timestamp = start_of_month.timestamp()

        balance_start_of_month = 0.0
        for d in sorted(deals, key=lambda x: x.time):
            if d.time < start_timestamp:
                if d.type == mt5.DEAL_TYPE_BALANCE:
                    balance_start_of_month += d.profit
                elif d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
                    balance_start_of_month += d.profit + d.commission + d.swap

        if balance_start_of_month <= 0:
            return 0.0

        growth = (current_balance - balance_start_of_month) / balance_start_of_month * 100
        return growth
