"""MT5 Bridge Client - Connects to MT5 Bridge running on Windows host"""
import os
import httpx
from typing import Optional, List, Any
from datetime import datetime

MT5_BRIDGE_URL = os.environ.get('MT5_BRIDGE_URL', 'http://host.docker.internal:8001')

# MT5 Constants (must match MetaTrader5 module)
DEAL_TYPE_BUY = 0
DEAL_TYPE_SELL = 1
DEAL_TYPE_BALANCE = 2
DEAL_ENTRY_IN = 0
DEAL_ENTRY_OUT = 1


class DictAsObject:
    """Wrapper to access dict keys as attributes"""
    def __init__(self, data: dict):
        self._data = data or {}
        for key, value in self._data.items():
            setattr(self, key, value)


class MT5BridgeClient:
    """Client to communicate with MT5 Bridge service on Windows host"""

    # Expose constants as class attributes
    DEAL_TYPE_BUY = DEAL_TYPE_BUY
    DEAL_TYPE_SELL = DEAL_TYPE_SELL
    DEAL_TYPE_BALANCE = DEAL_TYPE_BALANCE
    DEAL_ENTRY_IN = DEAL_ENTRY_IN
    DEAL_ENTRY_OUT = DEAL_ENTRY_OUT

    def __init__(self):
        self.base_url = MT5_BRIDGE_URL
        self.client = httpx.Client(timeout=30.0)

    def _get(self, endpoint: str) -> Any:
        try:
            response = self.client.get(f"{self.base_url}{endpoint}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"MT5 Bridge error: {e}")
            return None

    def _post(self, endpoint: str, data: dict) -> Any:
        try:
            response = self.client.post(f"{self.base_url}{endpoint}", json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"MT5 Bridge error: {e}")
            return None

    def initialize(self, path: Optional[str] = None, login: int = None,
                   password: str = None, server: str = None, timeout: int = None) -> bool:
        """Initialize MT5 connection, optionally with credentials"""
        result = self._post("/initialize", {"path": path})
        if not result or not result.get("success", False):
            return False

        # If credentials provided, also login
        if login and password and server:
            return self.login(login, password, server)
        return True

    def shutdown(self) -> None:
        self._post("/shutdown", {})

    def login(self, login: int, password: str = None, server: str = None) -> bool:
        result = self._post("/login", {
            "login": login,
            "password": password,
            "server": server
        })
        return result.get("success", False) if result else False

    def account_info(self) -> Optional[DictAsObject]:
        result = self._get("/account_info")
        if result:
            return DictAsObject(result)
        return None

    def positions_get(self) -> Optional[tuple]:
        result = self._get("/positions")
        if result:
            return tuple(DictAsObject(p) for p in result)
        return None

    def history_deals_get(self, date_from: datetime, date_to: datetime) -> Optional[tuple]:
        result = self._post("/history_deals", {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat()
        })
        if result:
            return tuple(DictAsObject(d) for d in result)
        return None

    def history_orders_get(self, date_from: datetime, date_to: datetime) -> Optional[tuple]:
        """Get history orders - not yet implemented in bridge"""
        return None

    def last_error(self) -> tuple:
        result = self._get("/last_error")
        if result:
            return (result.get("code", 0), result.get("message", ""))
        return (0, "Bridge not available")

    def terminal_info(self) -> Optional[DictAsObject]:
        result = self._get("/terminal_info")
        if result:
            return DictAsObject(result)
        return None


# Singleton instance
mt5_bridge = MT5BridgeClient()
