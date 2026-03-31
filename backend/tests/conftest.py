"""Pytest configuration and fixtures"""
import pytest
from unittest.mock import MagicMock
from collections import namedtuple
from datetime import datetime
from services.mt5.shared_state import MT5SharedState


# --- MT5 Mock ---

def _make_mt5_mock():
    """Create a MagicMock that mimics the MetaTrader5 module"""
    mock = MagicMock()
    mock.DEAL_TYPE_BUY = 0
    mock.DEAL_TYPE_SELL = 1
    mock.DEAL_TYPE_BALANCE = 2
    mock.DEAL_ENTRY_IN = 0
    mock.DEAL_ENTRY_OUT = 1
    mock.DEAL_ENTRY_INOUT = 2
    return mock


@pytest.fixture
def mock_mt5():
    return _make_mt5_mock()


# --- Account Info namedtuple ---

AccountInfoNT = namedtuple("AccountInfo", [
    "balance", "equity", "margin", "margin_free", "margin_level",
    "profit", "leverage", "server", "name", "login", "currency",
    "company", "trade_mode"
])


def make_account_info(**kwargs):
    defaults = {
        "balance": 10000.0,
        "equity": 10000.0,
        "margin": 100.0,
        "margin_free": 9900.0,
        "margin_level": 10000.0,
        "profit": 0.0,
        "leverage": 100,
        "server": "RoboForex-ECN",
        "name": "Test Account",
        "login": 12345,
        "currency": "USD",
        "company": "RoboForex",
        "trade_mode": 2,
    }
    defaults.update(kwargs)
    return AccountInfoNT(**defaults)


@pytest.fixture
def mock_account_info():
    return make_account_info


# --- MT5SharedState pre-filled ---

@pytest.fixture
def mt5_shared_state():
    state = MT5SharedState()
    state.connected = True
    state.current_account_id = 12345
    state.peak_balance = 10000.0
    state.peak_equity = 10000.0
    state.initial_deposit = 5000.0
    state.max_drawdown = 500.0
    state.max_drawdown_percent = 5.0
    return state


# --- Deal factory ---

DealNT = namedtuple("Deal", [
    "ticket", "type", "entry", "profit", "commission", "swap",
    "volume", "symbol", "time", "price", "comment"
])


def make_deal(**kwargs):
    defaults = {
        "ticket": 1,
        "type": 0,  # DEAL_TYPE_BUY
        "entry": 1,  # DEAL_ENTRY_OUT
        "profit": 100.0,
        "commission": -1.0,
        "swap": 0.0,
        "volume": 0.1,
        "symbol": "EURUSD",
        "time": int(datetime(2024, 6, 15, 12, 0).timestamp()),
        "price": 1.1000,
        "comment": "",
    }
    defaults.update(kwargs)
    return DealNT(**defaults)


@pytest.fixture
def deal_factory():
    """Returns the make_deal factory function"""
    return make_deal


# --- Position factory ---

PositionNT = namedtuple("Position", [
    "ticket", "symbol", "type", "volume", "time",
    "price_open", "price_current", "profit", "sl", "tp"
])


def make_position(**kwargs):
    defaults = {
        "ticket": 1,
        "symbol": "EURUSD",
        "type": 0,  # BUY
        "volume": 0.1,
        "time": int(datetime(2024, 6, 15, 12, 0).timestamp()),
        "price_open": 1.1000,
        "price_current": 1.1050,
        "profit": 50.0,
        "sl": 1.0950,
        "tp": 1.1100,
    }
    defaults.update(kwargs)
    return PositionNT(**defaults)


@pytest.fixture
def position_factory():
    return make_position
