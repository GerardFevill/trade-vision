"""Tests for MT5 SummaryService"""
import pytest
from unittest.mock import MagicMock, patch
from services.mt5.summary_service import SummaryService
from models import AccountSummary
from tests.conftest import make_account_info, make_deal


@pytest.fixture
def mock_connector():
    return MagicMock()


@pytest.fixture
def mock_cache():
    cache = MagicMock()
    cache.is_cache_valid.return_value = False
    cache.load_accounts.return_value = None
    return cache


class TestGetAllAccountsSummary:
    @patch("services.mt5.summary_service.accounts_cache")
    @patch("services.mt5.summary_service.account_balance_history")
    @patch("services.mt5.summary_service.MT5_ACCOUNTS", [])
    def test_empty_accounts_config(self, mock_hist, mock_cache, mock_mt5, mt5_shared_state, mock_connector):
        mock_cache.is_cache_valid.return_value = False
        svc = SummaryService(mt5_shared_state, mock_mt5, mock_connector)
        result = svc.get_all_accounts_summary(use_cache=False)
        assert result == []

    @patch("services.mt5.summary_service.accounts_cache")
    @patch("services.mt5.summary_service.account_balance_history")
    @patch("services.mt5.summary_service.MT5_ACCOUNTS", [])
    def test_cache_hit_returns_cached(self, mock_hist, mock_cache, mock_mt5, mt5_shared_state, mock_connector):
        cached_accounts = [
            AccountSummary(
                id=1, name="Cached", broker="Test", server="srv",
                balance=5000, equity=5000, profit=100, profit_percent=2.0,
                drawdown=0, trades=10, win_rate=60, currency="USD",
                leverage=100, connected=True
            )
        ]
        mock_cache.is_cache_valid.return_value = True
        mock_cache.load_accounts.return_value = cached_accounts
        svc = SummaryService(mt5_shared_state, mock_mt5, mock_connector)
        result = svc.get_all_accounts_summary(use_cache=True)
        assert len(result) == 1
        assert result[0].name == "Cached"

    @patch("services.mt5.summary_service.accounts_cache")
    @patch("services.mt5.summary_service.account_balance_history")
    @patch("services.mt5.summary_service.MT5_ACCOUNTS", [
        {"id": 123, "name": "Test", "server": "srv", "password": "x", "terminal": "roboforex"}
    ])
    def test_connection_failed_returns_disconnected(self, mock_hist, mock_cache, mock_mt5, mt5_shared_state, mock_connector):
        mock_cache.is_cache_valid.return_value = False
        mock_connector.connect.return_value = False
        svc = SummaryService(mt5_shared_state, mock_mt5, mock_connector)
        result = svc.get_all_accounts_summary(use_cache=False)
        assert len(result) == 1
        assert result[0].connected is False
        assert result[0].balance == 0

    @patch("services.mt5.summary_service.accounts_cache")
    @patch("services.mt5.summary_service.account_balance_history")
    @patch("services.mt5.summary_service.MT5_ACCOUNTS", [
        {"id": 123, "name": "Test", "server": "srv", "password": "x", "terminal": "roboforex"}
    ])
    def test_profit_percent_calculation(self, mock_hist, mock_cache, mock_mt5, mt5_shared_state, mock_connector):
        mock_cache.is_cache_valid.return_value = False
        mock_connector.connect.return_value = True
        info = make_account_info(balance=12000, equity=12000, login=123, profit=2000, currency="USD", leverage=100)
        mock_mt5.account_info.return_value = info

        deals = [
            make_deal(ticket=1, type=2, entry=0, profit=10000),   # Deposit
        ]
        mock_mt5.history_deals_get.return_value = deals
        svc = SummaryService(mt5_shared_state, mock_mt5, mock_connector)
        result = svc.get_all_accounts_summary(use_cache=False)
        assert len(result) == 1
        # profit = balance - net_deposit = 12000 - 10000 = 2000
        # profit_percent = 2000/10000 * 100 = 20%
        assert result[0].profit == 2000
        assert result[0].profit_percent == 20.0

    @patch("services.mt5.summary_service.accounts_cache")
    @patch("services.mt5.summary_service.account_balance_history")
    @patch("services.mt5.summary_service.MT5_ACCOUNTS", [
        {"id": 123, "name": "Test", "server": "srv", "password": "x", "terminal": "roboforex"}
    ])
    def test_win_rate_calculation(self, mock_hist, mock_cache, mock_mt5, mt5_shared_state, mock_connector):
        mock_cache.is_cache_valid.return_value = False
        mock_connector.connect.return_value = True
        info = make_account_info(balance=10000, equity=10000, login=123)
        mock_mt5.account_info.return_value = info

        deals = [
            make_deal(ticket=1, type=2, entry=0, profit=10000),   # Deposit
            make_deal(ticket=2, type=0, entry=1, profit=100, commission=0, swap=0),   # Win
            make_deal(ticket=3, type=1, entry=1, profit=-50, commission=0, swap=0),   # Loss
            make_deal(ticket=4, type=0, entry=1, profit=80, commission=0, swap=0),    # Win
        ]
        mock_mt5.history_deals_get.return_value = deals
        svc = SummaryService(mt5_shared_state, mock_mt5, mock_connector)
        result = svc.get_all_accounts_summary(use_cache=False)
        # 2 wins out of 3 trades = 66.7%
        assert result[0].win_rate == pytest.approx(66.7, abs=0.1)
        assert result[0].trades == 3
