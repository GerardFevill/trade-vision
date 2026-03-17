"""MT5 Trade Service - Trade stats, history, and positions"""
from datetime import datetime, timedelta
from models import TradeStats, Trade, Position
from .shared_state import MT5SharedState


class TradeService:
    def __init__(self, state: MT5SharedState, mt5):
        self.state = state
        self.mt5 = mt5

    def get_trade_stats(self) -> TradeStats | None:
        mt5 = self.mt5

        deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
        if not deals:
            return self._empty_trade_stats()

        trades = [d for d in deals if d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL] and d.entry == mt5.DEAL_ENTRY_OUT]

        if not trades:
            return self._empty_trade_stats()

        profits = [t.profit + t.commission + t.swap for t in trades]
        winning = [p for p in profits if p > 0]
        losing = [p for p in profits if p < 0]

        longs = [t for t in trades if t.type == mt5.DEAL_TYPE_SELL]  # Close long = SELL
        shorts = [t for t in trades if t.type == mt5.DEAL_TYPE_BUY]  # Close short = BUY
        longs_won = len([t for t in longs if (t.profit + t.commission + t.swap) > 0])
        shorts_won = len([t for t in shorts if (t.profit + t.commission + t.swap) > 0])

        gross_profit = sum(winning) if winning else 0
        gross_loss = abs(sum(losing)) if losing else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

        # Consecutive wins/losses
        max_cons_wins, max_cons_losses = self._calc_consecutive(profits)

        # Average holding time
        avg_holding = 0.0
        orders = mt5.history_orders_get(datetime(2000, 1, 1), datetime.now())
        if orders and len(orders) > 1:
            holding_times = []
            for i in range(0, len(orders) - 1, 2):
                if i + 1 < len(orders):
                    diff = orders[i + 1].time_done - orders[i].time_done
                    if diff > 0:
                        holding_times.append(diff)
            avg_holding = sum(holding_times) / len(holding_times) if holding_times else 0

        return TradeStats(
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=(len(winning) / len(trades) * 100) if trades else 0,
            best_trade=max(profits) if profits else 0,
            worst_trade=min(profits) if profits else 0,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            profit_factor=profit_factor,
            average_profit=(sum(winning) / len(winning)) if winning else 0,
            average_loss=(sum(losing) / len(losing)) if losing else 0,
            max_consecutive_wins=max_cons_wins,
            max_consecutive_losses=max_cons_losses,
            longs_count=len(longs),
            shorts_count=len(shorts),
            longs_won=longs_won,
            shorts_won=shorts_won,
            avg_holding_time_seconds=avg_holding,
            expected_payoff=(sum(profits) / len(profits)) if profits else 0
        )

    def get_history_trades(self, days: int = 30) -> list[Trade]:
        mt5 = self.mt5

        from_date = datetime.now() - timedelta(days=days)
        deals = mt5.history_deals_get(from_date, datetime.now())
        if not deals:
            return []

        types = {0: "BUY", 1: "SELL", 2: "BALANCE", 6: "CORRECTION"}
        trades = []
        for d in deals:
            if d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
                trades.append(Trade(
                    ticket=d.ticket,
                    symbol=d.symbol,
                    type=types.get(d.type, "OTHER"),
                    volume=d.volume,
                    open_time=datetime.fromtimestamp(d.time),
                    open_price=d.price,
                    close_time=None,
                    close_price=None,
                    profit=d.profit,
                    commission=d.commission,
                    swap=d.swap,
                    comment=d.comment or ""
                ))
        return trades[-100:]  # Last 100

    def get_open_positions(self) -> list[Position]:
        mt5 = self.mt5

        positions = mt5.positions_get()
        if not positions:
            return []

        result = []
        for p in positions:
            result.append(Position(
                ticket=p.ticket,
                symbol=p.symbol,
                type="BUY" if p.type == 0 else "SELL",
                volume=p.volume,
                open_time=datetime.fromtimestamp(p.time),
                open_price=p.price_open,
                current_price=p.price_current,
                profit=p.profit,
                sl=p.sl if p.sl > 0 else None,
                tp=p.tp if p.tp > 0 else None
            ))
        return result

    def _calc_consecutive(self, profits):
        max_wins = max_losses = current_wins = current_losses = 0
        for p in profits:
            if p > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        return max_wins, max_losses

    def _empty_trade_stats(self):
        return TradeStats(
            total_trades=0, winning_trades=0, losing_trades=0, win_rate=0,
            best_trade=0, worst_trade=0, gross_profit=0, gross_loss=0,
            profit_factor=0, average_profit=0, average_loss=0,
            max_consecutive_wins=0, max_consecutive_losses=0,
            longs_count=0, shorts_count=0, longs_won=0, shorts_won=0,
            avg_holding_time_seconds=0, expected_payoff=0
        )
