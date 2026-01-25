"""MT5 Accounts configuration - loads from environment or local file"""
from typing import List, Dict
from config.settings import settings

# Try to load from local config file (for backward compatibility)
# Create accounts_local.py with MT5_ACCOUNTS_LOCAL list to use local config
try:
    from config.accounts_local import MT5_ACCOUNTS_LOCAL, MT5_TERMINALS_LOCAL
    _use_local = True
except ImportError:
    _use_local = False
    MT5_ACCOUNTS_LOCAL = []
    MT5_TERMINALS_LOCAL = {}


def get_mt5_terminals() -> Dict[str, str]:
    """Get MT5 terminal paths from settings or local config"""
    if _use_local and MT5_TERMINALS_LOCAL:
        return MT5_TERMINALS_LOCAL

    terminals = settings.mt5_terminals
    if terminals:
        return terminals

    # Default paths
    return {
        "roboforex": r"C:\Program Files\RoboForex MT5 Terminal\terminal64.exe",
        "icmarkets": r"C:\Program Files\MetaTrader 5 IC Markets Global\terminal64.exe",
    }


def get_mt5_accounts() -> List[dict]:
    """Get MT5 accounts from settings or local config"""
    if _use_local and MT5_ACCOUNTS_LOCAL:
        return MT5_ACCOUNTS_LOCAL

    accounts = settings.get_mt5_accounts()
    if accounts:
        return accounts

    return []


# For backward compatibility - these are now functions
MT5_TERMINALS = get_mt5_terminals()
MT5_ACCOUNTS = get_mt5_accounts()
