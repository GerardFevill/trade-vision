"""Tests for MT5 AccountService"""
import pytest
from unittest.mock import patch
from datetime import datetime
from services.mt5.account_service import AccountService
from tests.conftest import make_deal, make_account_info


class TestGetAccountInfo:
    def test_returns_none_when_no_info(self, mock_mt5, mt5_shared_state):
        mock_mt5.account_info.return_value = None
        svc = AccountService(mt5_shared_state, mock_mt5)
        assert svc.get_account_info() is None

    def test_correct_mapping(self, mock_mt5, mt5_shared_state):
        info = make_account_info(
            balance=12345.67, equity=12300.0, margin=200.0,
            margin_free=12100.0, margin_level=6150.0, profit=45.67,
            leverage=200, server="TestServer", name="My Account",
            login=99999, currency="EUR"
        )
        mock_mt5.account_info.return_value = info
        svc = AccountService(mt5_shared_state, mock_mt5)
        result = svc.get_account_info()
        assert result.balance == 12345.67
        assert result.equity == 12300.0
        assert result.leverage == 200
        assert result.currency == "EUR"
        assert result.login == 99999

    def test_trade_mode_demo(self, mock_mt5, mt5_shared_state):
        info = make_account_info(trade_mode=0)
        mock_mt5.account_info.return_value = info
        svc = AccountService(mt5_shared_state, mock_mt5)
        result = svc.get_account_info()
        assert result.trade_mode == "Demo"

    def test_trade_mode_contest(self, mock_mt5, mt5_shared_state):
        info = make_account_info(trade_mode=1)
        mock_mt5.account_info.return_value = info
        svc = AccountService(mt5_shared_state, mock_mt5)
        result = svc.get_account_info()
        assert result.trade_mode == "Contest"

    def test_trade_mode_real(self, mock_mt5, mt5_shared_state):
        info = make_account_info(trade_mode=2)
        mock_mt5.account_info.return_value = info
        svc = AccountService(mt5_shared_state, mock_mt5)
        result = svc.get_account_info()
        assert result.trade_mode == "Real"

    def test_margin_level_none(self, mock_mt5, mt5_shared_state):
        info = make_account_info(margin_level=0)
        mock_mt5.account_info.return_value = info
        svc = AccountService(mt5_shared_state, mock_mt5)
        result = svc.get_account_info()
        assert result.margin_level is None


class TestGetCurrentMonthProfit:
    def test_returns_none_when_no_info(self, mock_mt5, mt5_shared_state):
        mock_mt5.account_info.return_value = None
        svc = AccountService(mt5_shared_state, mock_mt5)
        assert svc.get_current_month_profit() is None

    @patch("services.mt5.account_service.datetime")
    def test_no_deals(self, mock_datetime, mock_mt5, mt5_shared_state):
        mock_datetime.now.return_value = datetime(2024, 6, 15)
        mock_datetime.side_effect = lambda *a, **kw: datetime(*a, **kw)
        info = make_account_info(balance=10000.0)
        mock_mt5.account_info.return_value = info
        mock_mt5.history_deals_get.return_value = None
        svc = AccountService(mt5_shared_state, mock_mt5)
        result = svc.get_current_month_profit()
        assert result["profit"] == 0.0
        assert result["current_balance"] == 10000.0

    def test_with_deposits_and_trades(self, mock_mt5, mt5_shared_state):
        info = make_account_info(balance=12000.0)
        mock_mt5.account_info.return_value = info

        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1)
        before_month = int(start_of_month.timestamp()) - 86400  # Day before

        deals = [
            # Before month: deposit of 10000
            make_deal(ticket=1, type=2, profit=10000, time=before_month),
            # This month: deposit of 1000
            make_deal(ticket=2, type=2, profit=1000, time=int(start_of_month.timestamp()) + 3600),
        ]
        mock_mt5.history_deals_get.return_value = deals
        svc = AccountService(mt5_shared_state, mock_mt5)
        result = svc.get_current_month_profit()
        # starting = 10000 (before month balance) + 1000 (deposit) - 0 (no withdrawal) = 11000
        # profit = 12000 - 11000 = 1000
        assert result["profit"] == 1000.0
        assert result["deposits"] == 1000.0
        assert result["withdrawals"] == 0.0
