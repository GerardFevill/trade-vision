"""Tests for SyncService - pure calculation methods (_calc_sharpe_ratio, _calc_max_drawdown, _calc_consecutive)"""
import pytest
from unittest.mock import MagicMock


# We need to set up a mt5 mock before importing sync_service since it tries to import MetaTrader5
_mt5_module_mock = MagicMock()
_mt5_module_mock.DEAL_TYPE_BUY = 0
_mt5_module_mock.DEAL_TYPE_SELL = 1
_mt5_module_mock.DEAL_TYPE_BALANCE = 2
_mt5_module_mock.DEAL_ENTRY_IN = 0
_mt5_module_mock.DEAL_ENTRY_OUT = 1

from services.sync_service import SyncService


@pytest.fixture
def svc():
    return SyncService()


# --- _calc_sharpe_ratio() ---

class TestCalcSharpeRatio:
    def test_less_than_10_trades_returns_zero(self, svc):
        assert svc._calc_sharpe_ratio([10, 20, 30]) == 0.0

    def test_exactly_10_trades_same_value(self, svc):
        profits = [100] * 10
        # std = 0 → returns 0
        assert svc._calc_sharpe_ratio(profits) == 0.0

    def test_all_same_profit_std_zero_returns_zero(self, svc):
        profits = [50.0] * 20
        assert svc._calc_sharpe_ratio(profits) == 0.0

    def test_mixed_profits_positive_sharpe(self, svc):
        profits = [100, 50, 80, 120, 90, 70, 110, 60, 95, 85]
        result = svc._calc_sharpe_ratio(profits)
        assert result > 0  # All positive profits → positive Sharpe

    def test_mixed_positive_negative(self, svc):
        profits = [100, -50, 80, -30, 60, -20, 90, -40, 70, -10]
        result = svc._calc_sharpe_ratio(profits)
        # avg is positive (30), so Sharpe is positive
        assert result > 0

    def test_all_negative_returns_negative_sharpe(self, svc):
        profits = [-10, -20, -30, -40, -50, -60, -70, -80, -90, -100]
        result = svc._calc_sharpe_ratio(profits)
        assert result < 0

    def test_empty_list_returns_zero(self, svc):
        assert svc._calc_sharpe_ratio([]) == 0.0


# --- _calc_max_drawdown() ---

class _FakeDeal:
    """Minimal deal mock for drawdown calculation"""
    def __init__(self, deal_type, profit, commission=0, swap=0, time=0):
        self.type = deal_type
        self.profit = profit
        self.commission = commission
        self.swap = swap
        self.time = time


class TestCalcMaxDrawdown:
    def test_empty_deals_returns_zeros(self, svc):
        dd, dd_pct, peak = svc._calc_max_drawdown([])
        assert dd == 0
        assert dd_pct == 0
        assert peak == 0

    def test_single_deposit_no_drawdown(self, svc):
        deals = [_FakeDeal(2, 10000, time=1)]
        dd, dd_pct, peak = svc._calc_max_drawdown(deals)
        assert dd == 0
        assert dd_pct == 0
        assert peak == 10000

    def test_deposit_then_loss(self, svc):
        deals = [
            _FakeDeal(2, 10000, time=1),      # Deposit → balance=10000
            _FakeDeal(1, -2000, time=2),       # Losing SELL trade → balance=8000
        ]
        dd, dd_pct, peak = svc._calc_max_drawdown(deals)
        assert dd == 2000
        assert dd_pct == 20.0
        assert peak == 10000

    def test_recovery_after_drawdown(self, svc):
        deals = [
            _FakeDeal(2, 10000, time=1),      # Deposit
            _FakeDeal(1, -3000, time=2),       # Loss: balance=7000
            _FakeDeal(0, 5000, time=3),        # Win: balance=12000
        ]
        dd, dd_pct, peak = svc._calc_max_drawdown(deals)
        assert dd == 3000
        assert dd_pct == 30.0
        assert peak == 12000  # New peak after recovery


# --- _calc_consecutive_wins / losses ---

class TestCalcConsecutive:
    def test_empty_list(self, svc):
        assert svc._calc_consecutive_wins([]) == 0
        assert svc._calc_consecutive_losses([]) == 0

    def test_all_wins(self, svc):
        assert svc._calc_consecutive_wins([10, 20, 30]) == 3

    def test_all_losses(self, svc):
        assert svc._calc_consecutive_losses([-10, -20, -30]) == 3

    def test_alternating(self, svc):
        profits = [10, -5, 20, -10, 30]
        assert svc._calc_consecutive_wins(profits) == 1
        assert svc._calc_consecutive_losses(profits) == 1

    def test_streak_in_middle(self, svc):
        profits = [-5, 10, 20, 30, -10]
        assert svc._calc_consecutive_wins(profits) == 3
