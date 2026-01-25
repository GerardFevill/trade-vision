"""Mock MetaTrader5 module for Linux/Docker deployment"""
import os
from datetime import datetime
from collections import namedtuple

# Check if we're in Docker/Linux mode
IS_MOCK = os.environ.get('MT5_MOCK', 'false').lower() == 'true' or os.name != 'nt'

# Named tuples for MT5 data structures
AccountInfo = namedtuple('AccountInfo', [
    'login', 'server', 'balance', 'equity', 'margin', 'margin_free',
    'margin_level', 'profit', 'currency', 'leverage', 'name', 'company'
])

TradePosition = namedtuple('TradePosition', [
    'ticket', 'symbol', 'type', 'volume', 'price_open', 'price_current',
    'profit', 'swap', 'time', 'sl', 'tp', 'magic', 'comment'
])

TradeDeal = namedtuple('TradeDeal', [
    'ticket', 'order', 'time', 'type', 'entry', 'symbol', 'volume',
    'price', 'profit', 'swap', 'commission', 'magic', 'comment'
])

# Constants
TIMEFRAME_H1 = 16385
DEAL_TYPE_BUY = 0
DEAL_TYPE_SELL = 1
DEAL_ENTRY_IN = 0
DEAL_ENTRY_OUT = 1
ORDER_TYPE_BUY = 0
ORDER_TYPE_SELL = 1
POSITION_TYPE_BUY = 0
POSITION_TYPE_SELL = 1

def initialize(path=None):
    """Mock initialize - always returns True in mock mode"""
    return True

def shutdown():
    """Mock shutdown"""
    pass

def login(login, password=None, server=None, timeout=None):
    """Mock login - always returns True"""
    return True

def account_info():
    """Mock account info - returns None (no live data)"""
    return None

def positions_get(symbol=None):
    """Mock positions - returns empty tuple"""
    return ()

def history_deals_get(date_from=None, date_to=None, group=None):
    """Mock history deals - returns empty tuple"""
    return ()

def symbol_info_tick(symbol):
    """Mock symbol tick - returns None"""
    return None

def last_error():
    """Mock last error"""
    return (0, "Mock mode - no MT5 connection")

def terminal_info():
    """Mock terminal info"""
    return None
