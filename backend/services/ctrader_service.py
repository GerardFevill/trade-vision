"""cTrader Connector Service - Mirrors MT5Connector pattern for cTrader accounts"""
import time
from datetime import datetime, timedelta
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
        """Reconnect if needed"""
        if self.client and self.client.is_connected and self._app_authenticated:
            return True
        return self.connect()

    def _money_to_float(self, amount: int, money_digits: int) -> float:
        """Convert cTrader money amount (in cents) to float.
        e.g., 123456 with moneyDigits=2 -> 1234.56
        """
        return amount / (10 ** money_digits)

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

        # Get deal history for trade stats
        now_ms = int(time.time() * 1000)
        start_ms = int((datetime(2000, 1, 1).timestamp()) * 1000)
        deals_res = self.client.get_deal_list(ctid, start_ms, now_ms)

        total_deposits = 0.0
        total_withdrawals = 0.0
        trades_count = 0
        winning_trades = 0

        if deals_res:
            deals = deals_res.get("deal", [])
            for deal in deals:
                deal_status = deal.get("dealStatus", "FILLED")
                if deal_status != "FILLED":
                    continue

                close_pnl = self._money_to_float(
                    int(deal.get("closePositionDetail", {}).get("grossProfit", 0)),
                    money_digits
                ) if deal.get("closePositionDetail") else 0

                # DEPOSIT / WITHDRAW type deals
                deal_type = deal.get("tradeSide")
                is_deposit = deal.get("dealType") == "DEPOSIT"
                is_withdraw = deal.get("dealType") == "WITHDRAW"

                if is_deposit:
                    amount = self._money_to_float(
                        int(deal.get("filledVolume", 0)), money_digits
                    )
                    total_deposits += abs(amount) if amount else 0
                elif is_withdraw:
                    amount = self._money_to_float(
                        int(deal.get("filledVolume", 0)), money_digits
                    )
                    total_withdrawals += abs(amount) if amount else 0
                elif deal.get("closePositionDetail"):
                    # Closed trade
                    trades_count += 1
                    swap = self._money_to_float(
                        int(deal.get("closePositionDetail", {}).get("swap", 0)),
                        money_digits
                    )
                    commission = self._money_to_float(
                        int(deal.get("commission", 0)), money_digits
                    )
                    net_pnl = close_pnl + swap + commission
                    if net_pnl > 0:
                        winning_trades += 1

        # Calculate profit
        net_deposit = total_deposits - total_withdrawals
        profit = balance - net_deposit if net_deposit > 0 else 0
        profit_percent = (profit / net_deposit * 100) if net_deposit > 0 else 0

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
