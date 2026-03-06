"""cTrader accounts configuration loader"""
from typing import List, Dict

try:
    from config.ctrader_accounts_local import (
        CTRADER_CLIENT_ID,
        CTRADER_CLIENT_SECRET,
        CTRADER_ACCESS_TOKEN,
        CTRADER_REFRESH_TOKEN,
        CTRADER_ACCOUNTS as _CTRADER_ACCOUNTS_LOCAL,
        CTRADER_API_HOST,
        CTRADER_API_PORT,
    )
    _ctrader_available = True
except ImportError:
    _ctrader_available = False
    CTRADER_CLIENT_ID = ""
    CTRADER_CLIENT_SECRET = ""
    CTRADER_ACCESS_TOKEN = ""
    CTRADER_REFRESH_TOKEN = ""
    _CTRADER_ACCOUNTS_LOCAL = []
    CTRADER_API_HOST = "live.ctraderapi.com"
    CTRADER_API_PORT = 5035


def is_ctrader_configured() -> bool:
    """Check if cTrader is configured with valid tokens"""
    return _ctrader_available and bool(CTRADER_ACCESS_TOKEN)


def get_ctrader_credentials() -> Dict[str, str]:
    """Get cTrader API credentials"""
    return {
        "client_id": CTRADER_CLIENT_ID,
        "client_secret": CTRADER_CLIENT_SECRET,
        "access_token": CTRADER_ACCESS_TOKEN,
        "refresh_token": CTRADER_REFRESH_TOKEN,
    }


def get_ctrader_accounts() -> List[dict]:
    """Get configured cTrader accounts"""
    if _ctrader_available:
        return list(_CTRADER_ACCOUNTS_LOCAL)
    return []


def get_ctrader_endpoint() -> tuple:
    """Get cTrader API WebSocket endpoint (host, port)"""
    return (CTRADER_API_HOST, CTRADER_API_PORT)
