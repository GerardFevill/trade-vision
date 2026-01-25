"""MT5 Bridge Client - Connects to MT5 Bridge running on Windows host"""
import os
import httpx
from typing import Optional, List, Any
from datetime import datetime

MT5_BRIDGE_URL = os.environ.get('MT5_BRIDGE_URL', 'http://host.docker.internal:8001')


class MT5BridgeClient:
    """Client to communicate with MT5 Bridge service on Windows host"""

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

    def initialize(self, path: Optional[str] = None) -> bool:
        result = self._post("/initialize", {"path": path})
        return result.get("success", False) if result else False

    def shutdown(self) -> None:
        self._post("/shutdown", {})

    def login(self, login: int, password: str, server: str) -> bool:
        result = self._post("/login", {
            "login": login,
            "password": password,
            "server": server
        })
        return result.get("success", False) if result else False

    def account_info(self) -> Optional[dict]:
        return self._get("/account_info")

    def positions_get(self) -> List[dict]:
        result = self._get("/positions")
        return result if result else []

    def history_deals_get(self, date_from: datetime, date_to: datetime) -> List[dict]:
        result = self._post("/history_deals", {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat()
        })
        return result if result else []

    def last_error(self) -> tuple:
        result = self._get("/last_error")
        if result:
            return (result.get("code", 0), result.get("message", ""))
        return (0, "Bridge not available")


# Singleton instance
mt5_bridge = MT5BridgeClient()
