"""cTrader Connector Service - Mirrors MT5Connector pattern for cTrader accounts"""
import re
import time
from datetime import datetime
from typing import Optional
from models import AccountSummary
from config.ctrader_accounts import (
    is_ctrader_configured,
    get_ctrader_credentials,
    get_ctrader_accounts,
    get_ctrader_endpoint,
)
from config.logging import logger
from .ctrader_client import CTraderClient


class CTraderConnector:
    """Connector for cTrader accounts via Open API.

    Provides get_all_accounts_summary() returning list[AccountSummary],
    same format as MT5Connector for seamless merging in the API layer.
    """

    def __init__(self):
        self.client: Optional[CTraderClient] = None
        self._app_authenticated = False
        self._account_map: dict[int, int] = {}  # login -> ctidTraderAccountId
        self._last_connect_attempt = 0
        self._connect_cooldown = 30  # seconds between reconnect attempts

    def connect(self) -> bool:
        """Initialize connection: WebSocket + app auth + account discovery"""
        if not is_ctrader_configured():
            logger.info("cTrader not configured, skipping")
            return False

        # Cooldown to avoid hammering the API
        now = time.time()
        if now - self._last_connect_attempt < self._connect_cooldown:
            return self._app_authenticated
        self._last_connect_attempt = now

        try:
            host, port = get_ctrader_endpoint()
            creds = get_ctrader_credentials()

            # Create client and connect
            self.client = CTraderClient(host, port)
            if not self.client.connect():
                return False

            # Application auth
            if not self.client.application_auth(creds["client_id"], creds["client_secret"]):
                logger.error("cTrader application auth failed")
                self.client.disconnect()
                return False

            self._app_authenticated = True

            # Discover accounts: map login -> ctidTraderAccountId
            accounts = self.client.get_accounts_by_token(creds["access_token"])
            self._account_map.clear()
            for acc in accounts:
                login = acc.get("traderLogin")
                ctid = acc.get("ctidTraderAccountId")
                if login and ctid:
                    self._account_map[int(login)] = int(ctid)
                    logger.debug("cTrader account mapped",
                                 login=login, ctid=ctid,
                                 is_live=acc.get("isLive"))

            logger.info("cTrader connected",
                         accounts_discovered=len(self._account_map))
            return True

        except Exception as e:
            logger.error("cTrader connect failed", error=str(e))
            self._app_authenticated = False
            return False

    def disconnect(self):
        """Close the WebSocket connection"""
        if self.client:
            self.client.disconnect()
        self._app_authenticated = False
        self._account_map.clear()

    def _ensure_connected(self) -> bool:
        """Reconnect fresh to avoid stale TCP connections."""
        if self.client:
            self.client.disconnect()
        self._app_authenticated = False
        self._last_connect_attempt = 0  # Reset cooldown
        return self.connect()

    def _money_to_float(self, amount: int, money_digits: int) -> float:
        """Convert cTrader money amount (in cents) to float.
        e.g., 123456 with moneyDigits=2 -> 1234.56
        """
        return amount / (10 ** money_digits)

    def _scan_cashflow(self, ctid: int, registration_ts: int,
                        money_digits: int) -> dict:
        """Scan full cash flow history for copy investments and deposits.

        Iterates in 7-day windows from registration to now.
        Returns {
            "copy_strategies": [{"strategy": "spark", "net_invested": 100.0}],
            "total_deposits": 500.0,
            "total_withdrawals": 100.0,
        }
        """
        strategies: dict[str, float] = {}
        total_deposits = 0.0
        total_withdrawals = 0.0
        window_ms = 7 * 24 * 3600 * 1000  # 7 days in ms
        now_ms = int(time.time() * 1000)
        cursor = registration_ts

        while cursor < now_ms:
            end = min(cursor + window_ms, now_ms)
            try:
                items = self.client.get_cashflow_history(ctid, cursor, end)
            except Exception as e:
                logger.warning("CashFlow request failed", ctid=ctid, error=str(e))
                cursor = end
                time.sleep(0.1)
                continue

            for item in items:
                op_type = item.get("operationType", 0)
                delta = self._money_to_float(int(item.get("delta", 0)), money_digits)
                note = item.get("externalNote", "")

                if op_type in (30, 33):
                    # Copy invest/withdraw — extract strategy name
                    # Format: "Investment in strategy spark - transfer to account X"
                    match = re.search(r'strategy\s+(\w+)', note, re.IGNORECASE)
                    strategy_name = match.group(1) if match else "copy"

                    strategies.setdefault(strategy_name, 0.0)
                    if op_type == 30:
                        strategies[strategy_name] += abs(delta)
                    elif op_type == 33:
                        strategies[strategy_name] -= abs(delta)
                elif op_type == 0:
                    # External deposit or incoming transfer
                    if delta > 0:
                        total_deposits += delta
                elif op_type == 2:
                    # External withdrawal
                    total_withdrawals += abs(delta)
                elif op_type == 1:
                    # Internal transfer (positive=in, negative=out)
                    if delta > 0:
                        total_deposits += delta
                    else:
                        total_withdrawals += abs(delta)

            cursor = end
            time.sleep(0.1)

        copy_list = [
            {"strategy": name, "net_invested": round(amount, 2)}
            for name, amount in strategies.items()
            if amount > 0.01
        ]

        return {
            "copy_strategies": copy_list,
            "total_deposits": round(total_deposits, 2),
            "total_withdrawals": round(total_withdrawals, 2),
        }

    def _get_account_summary(self, login: int, account_config: dict) -> Optional[AccountSummary]:
        """Fetch summary for a single cTrader account"""
        ctid = self._account_map.get(login)
        if ctid is None:
            logger.warning("cTrader account not found in API", login=login)
            return None

        creds = get_ctrader_credentials()

        # Authenticate this account
        if not self.client.account_auth(ctid, creds["access_token"]):
            logger.error("cTrader account auth failed", login=login)
            return None

        # Get trader info (balance, leverage, currency)
        trader_res = self.client.get_trader(ctid)
        if not trader_res:
            logger.error("cTrader get_trader failed", login=login)
            return None

        trader = trader_res.get("trader", trader_res)
        money_digits = int(trader.get("moneyDigits", 2))
        balance_raw = int(trader.get("balance", 0))
        balance = self._money_to_float(balance_raw, money_digits)
        leverage_cents = int(trader.get("leverageInCents", 10000))
        leverage = leverage_cents // 100

        # Get open positions to calculate unrealized P/L
        reconcile = self.client.get_reconcile(ctid)
        unrealized_pnl = 0.0
        positions_count = 0

        if reconcile:
            positions = reconcile.get("position", [])
            for pos in positions:
                # swap + commission in money units
                swap = self._money_to_float(int(pos.get("swap", 0)), money_digits)
                commission = self._money_to_float(int(pos.get("commission", 0)), money_digits)
                # unrealizedPnl might be provided directly
                pnl = self._money_to_float(int(pos.get("unrealizedPnl", 0)), money_digits)
                unrealized_pnl += pnl + swap + commission
            positions_count = len(positions)

        equity = balance + unrealized_pnl

        # Scan cash flow history for copy investments and deposits
        copy_invested = None
        copy_strategy = None
        total_deposits = 0.0
        total_withdrawals = 0.0
        registration_ts = int(trader.get("registrationTimestamp", 0))

        if registration_ts > 0:
            try:
                cf_data = self._scan_cashflow(ctid, registration_ts, money_digits)

                # Copy trading detection
                copy_strategies = cf_data["copy_strategies"]
                if copy_strategies:
                    total_copy = sum(s["net_invested"] for s in copy_strategies)
                    if total_copy > 0.01:
                        copy_invested = round(total_copy, 2)
                        copy_strategy = ", ".join(s["strategy"] for s in copy_strategies)
                        balance = round(balance + total_copy, 2)
                        equity = round(equity + total_copy, 2)
                        logger.info("cTrader copy detected",
                                    login=login, copy_invested=copy_invested,
                                    strategies=copy_strategy)

                total_deposits = cf_data["total_deposits"]
                total_withdrawals = cf_data["total_withdrawals"]
            except Exception as e:
                logger.warning("Cash flow scan failed", login=login, error=str(e))

        # Get deal history for trade stats (single request, last 30 days)
        trades_count = 0
        winning_trades = 0

        if registration_ts > 0:
            now_ms = int(time.time() * 1000)
            # Use last 30 days only (within API limits, avoids rate limiting)
            start_ms = max(registration_ts, now_ms - 30 * 24 * 3600 * 1000)
            window_ms = 7 * 24 * 3600 * 1000
            cursor = start_ms
            while cursor < now_ms:
                end = min(cursor + window_ms, now_ms)
                try:
                    deals_res = self.client.get_deal_list(ctid, cursor, end)
                except Exception:
                    break

                if deals_res:
                    for deal in deals_res.get("deal", []):
                        if deal.get("closePositionDetail"):
                            trades_count += 1
                            cpd = deal["closePositionDetail"]
                            gross = self._money_to_float(
                                int(cpd.get("grossProfit", 0)), money_digits)
                            swap = self._money_to_float(
                                int(cpd.get("swap", 0)), money_digits)
                            comm = self._money_to_float(
                                int(cpd.get("commission", 0)), money_digits)
                            if gross + swap + comm > 0:
                                winning_trades += 1

                cursor = end
                time.sleep(0.2)

        # Calculate profit: total PnL = current equity + money withdrawn - money deposited
        profit = equity + total_withdrawals - total_deposits
        profit_percent = (profit / total_deposits * 100) if total_deposits > 0 else 0

        # Drawdown (simple: peak vs current equity)
        peak = max(balance, equity)
        drawdown_pct = max(0, (peak - equity) / peak * 100) if peak > 0 else 0

        win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0

        return AccountSummary(
            id=login,
            name=account_config.get("name", f"cTrader-{login}"),
            broker="Fusion Markets",
            server="cTrader",
            balance=round(balance, 2),
            equity=round(equity, 2),
            profit=round(profit, 2),
            profit_percent=round(profit_percent, 2),
            drawdown=round(drawdown_pct, 2),
            trades=trades_count,
            win_rate=round(win_rate, 1),
            currency="USD",
            leverage=leverage,
            connected=True,
            client=account_config.get("client"),
            copy_invested=copy_invested,
            copy_strategy=copy_strategy,
        )

    def get_all_accounts_summary(self) -> list[AccountSummary]:
        """Get summaries for all configured cTrader accounts.

        Returns list[AccountSummary] in the same format as MT5Connector.
        """
        if not self._ensure_connected():
            # Return disconnected placeholders
            return self._disconnected_summaries()

        configured_accounts = get_ctrader_accounts()
        summaries = []

        for acc_config in configured_accounts:
            login = acc_config["login"]
            try:
                summary = self._get_account_summary(login, acc_config)
                if summary:
                    summaries.append(summary)
                else:
                    summaries.append(self._disconnected_summary(login, acc_config))
            except Exception as e:
                logger.error("cTrader account error", login=login, error=str(e))
                summaries.append(self._disconnected_summary(login, acc_config))

        return summaries

    def _disconnected_summary(self, login: int, acc_config: dict) -> AccountSummary:
        """Create a disconnected AccountSummary placeholder"""
        return AccountSummary(
            id=login,
            name=acc_config.get("name", f"cTrader-{login}"),
            broker="Fusion Markets",
            server="cTrader",
            balance=0, equity=0, profit=0, profit_percent=0,
            drawdown=0, trades=0, win_rate=0,
            currency="USD", leverage=0, connected=False,
            client=acc_config.get("client"),
        )

    def _disconnected_summaries(self) -> list[AccountSummary]:
        """Return disconnected placeholders for all configured accounts"""
        return [
            self._disconnected_summary(acc["login"], acc)
            for acc in get_ctrader_accounts()
        ]


# Global instance
ctrader_connector = CTraderConnector()
