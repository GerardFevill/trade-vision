"""Tests for MT5 RiskService"""
import pytest
from datetime import datetime
from services.mt5.risk_service import RiskService
from models import HistoryPoint


class TestGetRiskMetrics:
    def test_returns_none_when_no_account_info(self, mock_mt5, mt5_shared_state):
        mock_mt5.account_info.return_value = None
        svc = RiskService(mt5_shared_state, mock_mt5)
        assert svc.get_risk_metrics() is None

    def test_drawdown_calculation(self, mock_mt5, mt5_shared_state, mock_account_info):
        info = mock_account_info(equity=9500.0, balance=9500.0, margin=100.0, profit=-500.0)
        mock_mt5.account_info.return_value = info
        mt5_shared_state.peak_equity = 10000.0
        svc = RiskService(mt5_shared_state, mock_mt5)
        result = svc.get_risk_metrics()
        assert result.current_drawdown == 500.0
        assert result.current_drawdown_percent == pytest.approx(5.0)

    def test_zero_equity_no_divide_error(self, mock_mt5, mt5_shared_state, mock_account_info):
        info = mock_account_info(equity=0, balance=0, margin=0, profit=0, margin_free=0, margin_level=0)
        mock_mt5.account_info.return_value = info
        mt5_shared_state.peak_equity = 0
        svc = RiskService(mt5_shared_state, mock_mt5)
        result = svc.get_risk_metrics()
        assert result.current_drawdown_percent == 0
        assert result.max_deposit_load == 0

    def test_recovery_factor(self, mock_mt5, mt5_shared_state, mock_account_info):
        info = mock_account_info(balance=15000.0, equity=15000.0, profit=10000.0)
        mock_mt5.account_info.return_value = info
        mt5_shared_state.initial_deposit = 5000.0
        mt5_shared_state.max_drawdown = 2000.0
        svc = RiskService(mt5_shared_state, mock_mt5)
        result = svc.get_risk_metrics()
        # recovery = (15000 - 5000) / 2000 = 5.0
        assert result.recovery_factor == 5.0

    def test_sharpe_ratio_with_enough_history(self, mock_mt5, mt5_shared_state, mock_account_info):
        info = mock_account_info()
        mock_mt5.account_info.return_value = info
        # Add 12 history points with varying equity
        now = datetime.now()
        for i in range(12):
            mt5_shared_state.history.append(HistoryPoint(
                balance=10000 + i * 100,
                equity=10000 + i * 100,
                drawdown=0, drawdown_percent=0,
                timestamp=now
            ))
        svc = RiskService(mt5_shared_state, mock_mt5)
        result = svc.get_risk_metrics()
        assert result.sharpe_ratio > 0  # Monotonically increasing equity → positive Sharpe

    def test_sharpe_ratio_insufficient_history(self, mock_mt5, mt5_shared_state, mock_account_info):
        info = mock_account_info()
        mock_mt5.account_info.return_value = info
        # Only 5 history points
        now = datetime.now()
        for i in range(5):
            mt5_shared_state.history.append(HistoryPoint(
                balance=10000, equity=10000, drawdown=0, drawdown_percent=0, timestamp=now
            ))
        svc = RiskService(mt5_shared_state, mock_mt5)
        result = svc.get_risk_metrics()
        assert result.sharpe_ratio == 0

    def test_deposit_load(self, mock_mt5, mt5_shared_state, mock_account_info):
        info = mock_account_info(margin=500.0, equity=10000.0)
        mock_mt5.account_info.return_value = info
        svc = RiskService(mt5_shared_state, mock_mt5)
        result = svc.get_risk_metrics()
        assert result.max_deposit_load == pytest.approx(5.0)


class TestGetDailyDrawdown:
    def test_empty_history(self, mock_mt5, mt5_shared_state):
        svc = RiskService(mt5_shared_state, mock_mt5)
        assert svc.get_daily_drawdown() == []

    def test_single_day(self, mock_mt5, mt5_shared_state):
        now = datetime(2024, 6, 15, 10, 0)
        mt5_shared_state.history.append(HistoryPoint(
            balance=10000, equity=10000, drawdown=0, drawdown_percent=0, timestamp=now
        ))
        mt5_shared_state.history.append(HistoryPoint(
            balance=9500, equity=9500, drawdown=500, drawdown_percent=5, timestamp=datetime(2024, 6, 15, 14, 0)
        ))
        svc = RiskService(mt5_shared_state, mock_mt5)
        result = svc.get_daily_drawdown()
        assert len(result) == 1
        assert result[0].date == "2024-06-15"
        assert result[0].drawdown_percent == 5.0

    def test_multi_day(self, mock_mt5, mt5_shared_state):
        mt5_shared_state.history.append(HistoryPoint(
            balance=10000, equity=10000, drawdown=0, drawdown_percent=0,
            timestamp=datetime(2024, 6, 14, 10, 0)
        ))
        mt5_shared_state.history.append(HistoryPoint(
            balance=9800, equity=9800, drawdown=200, drawdown_percent=2,
            timestamp=datetime(2024, 6, 15, 10, 0)
        ))
        svc = RiskService(mt5_shared_state, mock_mt5)
        result = svc.get_daily_drawdown()
        assert len(result) == 2
        assert result[0].date == "2024-06-14"
        assert result[1].date == "2024-06-15"
