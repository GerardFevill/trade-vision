"""MT5 Connector - Facade for all MT5 operations"""
import os
import time

MT5_MODE = os.environ.get('MT5_MODE', 'direct')

if MT5_MODE == 'bridge':
    from ..mt5_bridge_client import mt5_bridge as mt5
    MT5_AVAILABLE = True
else:
    try:
        import MetaTrader5 as mt5
        MT5_AVAILABLE = True
    except ImportError:
        from .. import mt5_mock as mt5
        MT5_AVAILABLE = False

from datetime import datetime
from models import ConnectionStatus
from db import history_db
from config import MT5_ACCOUNTS, MT5_TERMINALS
from config.logging import logger

from .shared_state import MT5SharedState
from .account_service import AccountService
from .trade_service import TradeService
from .risk_service import RiskService
from .history_service import HistoryService
from .monthly_growth_service import MonthlyGrowthService
from .summary_service import SummaryService


class MT5Connector:
    def __init__(self, history_max_size: int = 3600):
        self.state = MT5SharedState(history_max_size)
        self.history_max_size = history_max_size

        # Sub-services
        self._account = AccountService(self.state, mt5)
        self._trade = TradeService(self.state, mt5)
        self._risk = RiskService(self.state, mt5)
        self._history = HistoryService(self.state, mt5)
        self._monthly_growth = MonthlyGrowthService(self.state, mt5, connect_fn=self.connect)
        self._summary = SummaryService(self.state, mt5, connector=self)

    # --- Properties for backward compatibility ---

    @property
    def connected(self):
        return self.state.connected

    @connected.setter
    def connected(self, value):
        self.state.connected = value

    @property
    def current_account_id(self):
        return self.state.current_account_id

    @current_account_id.setter
    def current_account_id(self, value):
        self.state.current_account_id = value

    @property
    def current_terminal(self):
        return self.state.current_terminal

    @current_terminal.setter
    def current_terminal(self, value):
        self.state.current_terminal = value

    @property
    def peak_balance(self):
        return self.state.peak_balance

    @peak_balance.setter
    def peak_balance(self, value):
        self.state.peak_balance = value

    @property
    def peak_equity(self):
        return self.state.peak_equity

    @peak_equity.setter
    def peak_equity(self, value):
        self.state.peak_equity = value

    @property
    def initial_deposit(self):
        return self.state.initial_deposit

    @initial_deposit.setter
    def initial_deposit(self, value):
        self.state.initial_deposit = value

    @property
    def history(self):
        return self.state.history

    @property
    def max_drawdown(self):
        return self.state.max_drawdown

    @max_drawdown.setter
    def max_drawdown(self, value):
        self.state.max_drawdown = value

    @property
    def max_drawdown_percent(self):
        return self.state.max_drawdown_percent

    @max_drawdown_percent.setter
    def max_drawdown_percent(self, value):
        self.state.max_drawdown_percent = value

    # --- Connection methods ---

    def _reset_account_data(self):
        """Reset account-specific data"""
        self.state.reset()

    def _load_history_from_db(self, account_id: int):
        """Load history from database for a specific account"""
        db_history = history_db.load_history(account_id, days=730)
        self.state.history.clear()
        for point in db_history:
            self.state.history.append(point)
        if db_history:
            last_point = db_history[-1]
            self.state.peak_balance = last_point.balance
            self.state.peak_equity = last_point.equity
            self.state.max_drawdown = 0.0
            self.state.max_drawdown_percent = 0.0
            logger.info("History loaded for account", account_id=account_id, points=len(db_history))
        else:
            logger.info("No history for account, starting fresh", account_id=account_id)
            info = mt5.account_info()
            if info:
                self.state.peak_balance = info.balance
                self.state.peak_equity = info.equity

    def _calculate_initial_deposit(self):
        deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
        if deals:
            deposits = [d.profit for d in deals if d.type == mt5.DEAL_TYPE_BALANCE and d.profit > 0]
            self.state.initial_deposit = deposits[0] if deposits else 0

    def connect(self, account_id: int = None, retries: int = 2, timeout: int = 60000) -> bool:
        """Connect to MT5, optionally to a specific account"""
        switching_account = account_id and account_id != self.state.current_account_id

        if not account_id:
            if MT5_ACCOUNTS:
                account_id = MT5_ACCOUNTS[0]["id"]
            else:
                logger.warning("No accounts configured")
                return False

        account_config = None
        for acc in MT5_ACCOUNTS:
            if acc["id"] == account_id:
                account_config = acc
                break

        if not account_config:
            logger.error("Account not found in config", account_id=account_id)
            return False

        terminal_key = account_config.get("terminal", "roboforex")
        terminal_path = MT5_TERMINALS.get(terminal_key)

        for attempt in range(retries + 1):
            mt5.shutdown()

            init_params = {
                "login": account_config["id"],
                "password": account_config["password"],
                "server": account_config["server"],
                "timeout": timeout
            }

            if terminal_path:
                init_params["path"] = terminal_path

            if mt5.initialize(**init_params):
                logger.info("MT5 connected to account", account_id=account_id, server=account_config['server'])
                break
            else:
                error = mt5.last_error()
                logger.warning("MT5 connection failed", account_id=account_id, attempt=attempt + 1, max_attempts=retries + 1, error=str(error))
                if attempt < retries:
                    time.sleep(2)
                    continue
                return False

        self.state.current_account_id = account_id
        self.state.current_terminal = terminal_key

        if switching_account:
            self._reset_account_data()
            self._load_history_from_db(account_id)

        self.state.connected = True
        info = mt5.account_info()
        if info:
            if self.state.current_account_id != info.login:
                self.state.current_account_id = info.login
                self._reset_account_data()
                self._load_history_from_db(info.login)

            self.state.peak_balance = max(self.state.peak_balance, info.balance)
            self.state.peak_equity = max(self.state.peak_equity, info.equity)
            if self.state.initial_deposit == 0:
                self._calculate_initial_deposit()
        return True

    def disconnect(self):
        mt5.shutdown()
        self.state.connected = False

    def get_connection_status(self) -> ConnectionStatus:
        if not self.state.connected:
            return ConnectionStatus(connected=False, server=None, account=None, name=None, company=None)
        info = mt5.account_info()
        if not info:
            return ConnectionStatus(connected=False, server=None, account=None, name=None, company=None)
        return ConnectionStatus(
            connected=True,
            server=info.server,
            account=info.login,
            name=info.name,
            company=info.company
        )

    # --- Delegated methods (with auto-connect) ---

    def get_account_info(self):
        if not self.state.connected and not self.connect():
            return None
        return self._account.get_account_info()

    def get_account_stats(self):
        if not self.state.connected and not self.connect():
            return None
        return self._account.get_account_stats()

    def get_current_month_profit(self):
        if not self.state.connected and not self.connect():
            return None
        return self._account.get_current_month_profit()

    def get_trade_stats(self):
        if not self.state.connected and not self.connect():
            return None
        return self._trade.get_trade_stats()

    def get_history_trades(self, days: int = 30):
        if not self.state.connected and not self.connect():
            return []
        return self._trade.get_history_trades(days)

    def get_open_positions(self):
        if not self.state.connected and not self.connect():
            return []
        return self._trade.get_open_positions()

    def get_risk_metrics(self):
        if not self.state.connected and not self.connect():
            return None
        return self._risk.get_risk_metrics()

    def get_daily_drawdown(self):
        return self._risk.get_daily_drawdown()

    def reset_peak_balance(self):
        self._risk.reset_peak_balance()

    def get_history(self, limit: int = 60):
        return self._history.get_history(limit)

    def rebuild_history_from_deals(self):
        if not self.state.connected and not self.connect():
            return 0
        return self._history.rebuild_history_from_deals()

    def get_monthly_growth(self):
        if not self.state.connected and not self.connect():
            return []
        return self._monthly_growth.get_monthly_growth()

    def get_global_monthly_growth(self, use_cache: bool = True, cache_max_age_hours: int = 24):
        return self._monthly_growth.get_global_monthly_growth(use_cache, cache_max_age_hours)

    def get_all_accounts_summary(self, use_cache: bool = True, cache_max_age: int = 60):
        return self._summary.get_all_accounts_summary(use_cache, cache_max_age)

    def get_single_account_summary(self, account_id: int):
        return self._summary.get_single_account_summary(account_id)

    def get_full_dashboard(self):
        return self._summary.get_full_dashboard()


# Global instance
mt5_connector = MT5Connector()
