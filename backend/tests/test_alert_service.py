"""Tests for Alert Service - pure logic (check_condition, _get_metric_value)"""
import pytest
from services.alert_service import AlertService
from config.alerts import AlertType, AlertCondition


@pytest.fixture
def svc():
    return AlertService()


# --- check_condition() ---

class TestCheckCondition:
    def test_above_true(self, svc):
        assert svc.check_condition(AlertCondition.ABOVE, 15.0, 10.0) is True

    def test_above_false_when_equal(self, svc):
        assert svc.check_condition(AlertCondition.ABOVE, 10.0, 10.0) is False

    def test_above_false_when_below(self, svc):
        assert svc.check_condition(AlertCondition.ABOVE, 5.0, 10.0) is False

    def test_below_true(self, svc):
        assert svc.check_condition(AlertCondition.BELOW, 5.0, 10.0) is True

    def test_below_false_when_equal(self, svc):
        assert svc.check_condition(AlertCondition.BELOW, 10.0, 10.0) is False

    def test_equals_true_exact(self, svc):
        assert svc.check_condition(AlertCondition.EQUALS, 10.0, 10.0) is True

    def test_equals_true_within_tolerance(self, svc):
        assert svc.check_condition(AlertCondition.EQUALS, 10.005, 10.0) is True

    def test_equals_false_outside_tolerance(self, svc):
        assert svc.check_condition(AlertCondition.EQUALS, 10.02, 10.0) is False

    def test_unknown_condition_returns_false(self, svc):
        assert svc.check_condition("unknown_condition", 10.0, 10.0) is False


# --- _get_metric_value() ---

class TestGetMetricValue:
    def test_drawdown_maps_to_drawdown_percent(self, svc):
        metrics = {"drawdown_percent": 8.5}
        assert svc._get_metric_value(AlertType.DRAWDOWN, metrics) == 8.5

    def test_profit_maps_to_profit(self, svc):
        metrics = {"profit": 1500.0}
        assert svc._get_metric_value(AlertType.PROFIT, metrics) == 1500.0

    def test_loss_maps_to_profit(self, svc):
        metrics = {"profit": -200.0}
        assert svc._get_metric_value(AlertType.LOSS, metrics) == -200.0

    def test_balance_maps_to_balance(self, svc):
        metrics = {"balance": 50000.0}
        assert svc._get_metric_value(AlertType.BALANCE, metrics) == 50000.0

    def test_equity_maps_to_equity(self, svc):
        metrics = {"equity": 48000.0}
        assert svc._get_metric_value(AlertType.EQUITY, metrics) == 48000.0

    def test_margin_level_maps_to_margin_level(self, svc):
        metrics = {"margin_level": 250.0}
        assert svc._get_metric_value(AlertType.MARGIN_LEVEL, metrics) == 250.0

    def test_unknown_type_returns_none(self, svc):
        metrics = {"drawdown_percent": 5.0}
        assert svc._get_metric_value("unknown_type", metrics) is None

    def test_missing_key_returns_none(self, svc):
        metrics = {}
        assert svc._get_metric_value(AlertType.DRAWDOWN, metrics) is None
