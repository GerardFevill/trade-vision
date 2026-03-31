"""MT5 Summary Service - Multi-account summary and dashboard"""
from datetime import datetime
from models import AccountSummary, FullDashboard
from db import accounts_cache, account_balance_history
from config import MT5_ACCOUNTS
from config.logging import logger
from .shared_state import MT5SharedState


class SummaryService:
    def __init__(self, state: MT5SharedState, mt5, connector):
        self.state = state
        self.mt5 = mt5
        self.connector = connector

    def get_all_accounts_summary(self, use_cache: bool = True, cache_max_age: int = 60) -> list[AccountSummary]:
        if use_cache and accounts_cache.is_cache_valid(cache_max_age):
            cached = accounts_cache.load_accounts()
            if cached:
                return cached

        mt5 = self.mt5
        summaries = []

        for acc_config in MT5_ACCOUNTS:
            account_id = acc_config["id"]
            account_name = acc_config["name"]
            terminal_key = acc_config.get("terminal", "roboforex")
            broker_name = acc_config.get("broker") or ("IC Markets" if terminal_key == "icmarkets" else "RoboForex")
            client = acc_config.get("client")

            try:
                if not self.connector.connect(account_id):
                    summaries.append(AccountSummary(
                        id=account_id, name=account_name, broker=broker_name,
                        server=acc_config["server"], balance=0, equity=0, profit=0,
                        profit_percent=0, drawdown=0, trades=0, win_rate=0,
                        currency="USD", leverage=0, connected=False, client=client
                    ))
                    continue

                info = mt5.account_info()
                if not info:
                    continue

                deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
                total_deposits = 0.0
                total_withdrawals = 0.0
                trades_count = 0
                winning_trades = 0

                if deals:
                    for d in deals:
                        if d.type == mt5.DEAL_TYPE_BALANCE:
                            if d.profit > 0:
                                total_deposits += d.profit
                            else:
                                total_withdrawals += abs(d.profit)
                        elif d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL] and d.entry == mt5.DEAL_ENTRY_OUT:
                            trades_count += 1
                            if (d.profit + d.commission + d.swap) > 0:
                                winning_trades += 1

                net_deposit = total_deposits - total_withdrawals
                profit = info.balance - net_deposit if net_deposit > 0 else info.profit
                profit_percent = (profit / net_deposit * 100) if net_deposit > 0 else 0

                peak = max(info.balance, info.equity)
                current_dd_pct = max(0, (peak - info.equity) / peak * 100) if peak > 0 else 0

                win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0

                summaries.append(AccountSummary(
                    id=info.login, name=account_name,
                    broker=info.company or "RoboForex", server=info.server,
                    balance=round(info.balance, 2), equity=round(info.equity, 2),
                    profit=round(profit, 2), profit_percent=round(profit_percent, 2),
                    drawdown=round(current_dd_pct, 2), trades=trades_count,
                    win_rate=round(win_rate, 1), currency=info.currency,
                    leverage=info.leverage, connected=True, client=client
                ))

            except Exception as e:
                logger.error("Error for account", account_id=account_id, error=str(e))
                summaries.append(AccountSummary(
                    id=account_id, name=account_name, broker=broker_name,
                    server=acc_config["server"], balance=0, equity=0, profit=0,
                    profit_percent=0, drawdown=0, trades=0, win_rate=0,
                    currency="USD", leverage=0, connected=False, client=client
                ))

        if summaries:
            accounts_cache.save_accounts(summaries)
            account_balance_history.save_all_snapshots(summaries)

        return summaries

    def get_single_account_summary(self, account_id: int) -> AccountSummary | None:
        mt5 = self.mt5

        acc_config = None
        for acc in MT5_ACCOUNTS:
            if acc["id"] == account_id:
                acc_config = acc
                break

        if not acc_config:
            return None

        account_name = acc_config["name"]
        terminal_key = acc_config.get("terminal", "roboforex")
        broker_name = acc_config.get("broker") or ("IC Markets" if terminal_key == "icmarkets" else "RoboForex")
        client = acc_config.get("client")

        try:
            info = mt5.account_info()
            if not info:
                return None

            deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
            total_deposits = 0.0
            total_withdrawals = 0.0
            trades_count = 0
            winning_trades = 0

            if deals:
                for d in deals:
                    if d.type == mt5.DEAL_TYPE_BALANCE:
                        if d.profit > 0:
                            total_deposits += d.profit
                        else:
                            total_withdrawals += abs(d.profit)
                    elif d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL] and d.entry == mt5.DEAL_ENTRY_OUT:
                        trades_count += 1
                        if (d.profit + d.commission + d.swap) > 0:
                            winning_trades += 1

            net_deposit = total_deposits - total_withdrawals
            profit = info.balance - net_deposit if net_deposit > 0 else info.profit
            profit_percent = (profit / net_deposit * 100) if net_deposit > 0 else 0

            peak = max(info.balance, info.equity)
            current_dd_pct = max(0, (peak - info.equity) / peak * 100) if peak > 0 else 0

            win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0

            return AccountSummary(
                id=info.login, name=account_name,
                broker=info.company or broker_name, server=info.server,
                balance=round(info.balance, 2), equity=round(info.equity, 2),
                profit=round(profit, 2), profit_percent=round(profit_percent, 2),
                drawdown=round(current_dd_pct, 2), trades=trades_count,
                win_rate=round(win_rate, 1), currency=info.currency,
                leverage=info.leverage, connected=True, client=client
            )
        except Exception as e:
            logger.error("Error getting single account summary", account_id=account_id, error=str(e))
            return None

    def get_full_dashboard(self) -> FullDashboard | None:
        account = self.connector.get_account_info()
        stats = self.connector.get_account_stats()
        trade_stats = self.connector.get_trade_stats()
        risk = self.connector.get_risk_metrics()
        positions = self.connector.get_open_positions()
        monthly = self.connector.get_monthly_growth()

        if not all([account, stats, trade_stats, risk]):
            return None

        return FullDashboard(
            account=account,
            stats=stats,
            trade_stats=trade_stats,
            risk_metrics=risk,
            open_positions=positions,
            monthly_growth=monthly
        )
