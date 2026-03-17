"""MT5 History Service - Balance history and rebuild from deals"""
from datetime import datetime
from models import HistoryPoint
from db import history_db
from config.logging import logger
from .shared_state import MT5SharedState


class HistoryService:
    def __init__(self, state: MT5SharedState, mt5):
        self.state = state
        self.mt5 = mt5

    def get_history(self, limit: int = 60) -> list[HistoryPoint]:
        return list(self.state.history)[-limit:]

    def rebuild_history_from_deals(self) -> int:
        mt5 = self.mt5
        state = self.state

        deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
        if not deals:
            return 0

        sorted_deals = sorted(deals, key=lambda d: d.time)

        running_balance = 0.0
        peak_balance = 0.0
        peak_equity = 0.0
        points_added = 0
        last_date = None
        drawdown = 0.0
        drawdown_pct = 0.0

        for d in sorted_deals:
            deal_time = datetime.fromtimestamp(d.time)
            deal_date = deal_time.date()

            if d.type == mt5.DEAL_TYPE_BALANCE:
                running_balance += d.profit
            elif d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
                running_balance += d.profit + d.commission + d.swap

            if running_balance > peak_balance:
                peak_balance = running_balance
            peak_equity = peak_balance

            drawdown = max(0, peak_equity - running_balance)
            drawdown_pct = (drawdown / peak_equity * 100) if peak_equity > 0 else 0

            if last_date != deal_date:
                point = HistoryPoint(
                    balance=running_balance,
                    equity=running_balance,
                    drawdown=drawdown,
                    drawdown_percent=drawdown_pct,
                    timestamp=deal_time
                )
                state.history.append(point)
                if state.current_account_id:
                    history_db.save_point(point, state.current_account_id)
                points_added += 1
                last_date = deal_date

        state.peak_balance = peak_balance
        state.peak_equity = peak_equity
        if drawdown > state.max_drawdown:
            state.max_drawdown = drawdown
        if drawdown_pct > state.max_drawdown_percent:
            state.max_drawdown_percent = drawdown_pct

        logger.info("History rebuilt from MT5 deals", points_added=points_added)
        return points_added
