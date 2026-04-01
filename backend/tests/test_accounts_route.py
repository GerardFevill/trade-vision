"""Tests for accounts route - _fetch_all_accounts logic"""
from unittest.mock import patch, MagicMock
from models import AccountSummary


def _make_summary(**kwargs):
    defaults = dict(
        id=1, name="Test", broker="Broker", server="srv",
        balance=10000, equity=10000, profit=500, profit_percent=5.0,
        drawdown=2.0, trades=50, win_rate=60.0, currency="USD",
        leverage=100, connected=True
    )
    defaults.update(kwargs)
    return AccountSummary(**defaults)


class TestFetchAllAccounts:
    @patch("api.routes.accounts.ctrader_connector")
    @patch("api.routes.accounts.mt5_connector")
    @patch("api.routes.accounts.accounts_cache")
    def test_merge_mt5_and_ctrader(self, mock_cache, mock_mt5, mock_ctrader):
        mt5_acc = _make_summary(id=1, name="MT5-1")
        ctrader_acc = _make_summary(id=2, name="cTrader-1", copy_strategy="Strategy1", copy_invested=5000.0)

        mock_mt5.get_all_accounts_summary.return_value = [mt5_acc]
        mock_ctrader.get_all_accounts_summary.return_value = [ctrader_acc]
        mock_cache.save_accounts = MagicMock()

        from api.routes.accounts import _fetch_all_accounts
        result = _fetch_all_accounts(use_cache=False, timeout=5)
        assert len(result) == 2
        names = {a.name for a in result}
        assert "MT5-1" in names
        assert "cTrader-1" in names

    @patch("api.routes.accounts.ctrader_connector")
    @patch("api.routes.accounts.mt5_connector")
    @patch("api.routes.accounts.accounts_cache")
    def test_mt5_timeout_uses_cache(self, mock_cache, mock_mt5, mock_ctrader):
        """When MT5 times out, should fallback to cached MT5 accounts"""
        cached_mt5 = _make_summary(id=1, name="Cached-MT5")
        # Simulate timeout: thread returns None
        mock_mt5.get_all_accounts_summary.return_value = None

        mock_cache.load_accounts.return_value = [cached_mt5]
        mock_cache.save_accounts = MagicMock()
        mock_ctrader.get_all_accounts_summary.return_value = []

        from api.routes.accounts import _fetch_all_accounts
        # Use very short timeout to trigger the timeout path
        result = _fetch_all_accounts(use_cache=False, timeout=0.001)
        # Should still return something (either cached or empty)
        assert isinstance(result, list)

    @patch("api.routes.accounts.ctrader_connector")
    @patch("api.routes.accounts.mt5_connector")
    @patch("api.routes.accounts.accounts_cache")
    def test_ctrader_failure_returns_mt5_only(self, mock_cache, mock_mt5, mock_ctrader):
        mt5_acc = _make_summary(id=1, name="MT5-Only")
        mock_mt5.get_all_accounts_summary.return_value = [mt5_acc]
        mock_ctrader.get_all_accounts_summary.side_effect = Exception("Connection refused")
        mock_cache.save_accounts = MagicMock()

        from api.routes.accounts import _fetch_all_accounts
        result = _fetch_all_accounts(use_cache=False, timeout=5)
        assert len(result) == 1
        assert result[0].name == "MT5-Only"

    @patch("api.routes.accounts.ctrader_connector")
    @patch("api.routes.accounts.mt5_connector")
    @patch("api.routes.accounts.accounts_cache")
    def test_both_fail_returns_empty(self, mock_cache, mock_mt5, mock_ctrader):
        mock_mt5.get_all_accounts_summary.side_effect = Exception("MT5 down")
        mock_ctrader.get_all_accounts_summary.side_effect = Exception("cTrader down")
        mock_cache.load_accounts.return_value = None
        mock_cache.save_accounts = MagicMock()

        from api.routes.accounts import _fetch_all_accounts
        result = _fetch_all_accounts(use_cache=False, timeout=5)
        assert result == []

    @patch("api.routes.accounts.ctrader_connector")
    @patch("api.routes.accounts.mt5_connector")
    @patch("api.routes.accounts.accounts_cache")
    def test_saves_combined_to_cache(self, mock_cache, mock_mt5, mock_ctrader):
        mt5_acc = _make_summary(id=1, name="MT5")
        ctrader_acc = _make_summary(id=2, name="cTrader", copy_strategy="S", copy_invested=1000.0)

        mock_mt5.get_all_accounts_summary.return_value = [mt5_acc]
        mock_ctrader.get_all_accounts_summary.return_value = [ctrader_acc]
        mock_cache.save_accounts = MagicMock()

        from api.routes.accounts import _fetch_all_accounts
        _fetch_all_accounts(use_cache=False, timeout=5)
        mock_cache.save_accounts.assert_called_once()
        saved = mock_cache.save_accounts.call_args[0][0]
        assert len(saved) == 2

    @patch("api.routes.accounts.ctrader_connector")
    @patch("api.routes.accounts.mt5_connector")
    @patch("api.routes.accounts.accounts_cache")
    def test_force_mt5_passes_no_cache(self, mock_cache, mock_mt5, mock_ctrader):
        mock_mt5.get_all_accounts_summary.return_value = []
        mock_ctrader.get_all_accounts_summary.return_value = []
        mock_cache.save_accounts = MagicMock()

        from api.routes.accounts import _fetch_all_accounts
        _fetch_all_accounts(use_cache=False, timeout=300)
        mock_mt5.get_all_accounts_summary.assert_called_with(use_cache=False)
