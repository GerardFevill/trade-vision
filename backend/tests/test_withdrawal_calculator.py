"""Tests for Withdrawal Calculator"""
import pytest
from services.portfolio.withdrawal_calculator import (
    WITHDRAWAL_PERCENTAGES,
    calculate_standard_preview,
)


class TestWithdrawalPercentages:
    def test_securise_is_50_percent(self):
        assert WITHDRAWAL_PERCENTAGES["Securise"] == 0.50

    def test_modere_is_80_percent(self):
        assert WITHDRAWAL_PERCENTAGES["Modere"] == 0.80

    def test_agressif_is_90_percent(self):
        assert WITHDRAWAL_PERCENTAGES["Agressif"] == 0.90

    def test_conservateur_is_70_percent(self):
        assert WITHDRAWAL_PERCENTAGES["Conservateur"] == 0.70

    def test_unknown_type_defaults_to_80(self):
        pct = WITHDRAWAL_PERCENTAGES.get("Unknown", 0.80)
        assert pct == 0.80


class _FakePortfolioAccount:
    def __init__(self, lot_factor, account=True):
        self.lot_factor = lot_factor
        self.account = account


class _FakeAccount:
    def __init__(self, id=1, name="Test", currency="EUR"):
        self.id = id
        self.name = name
        self.currency = currency


class _FakeDetail:
    def __init__(self, accounts):
        self.accounts = accounts


class TestCalculateStandardPreview:
    def _make_data(self, lot_factor=1.0, starting=10000, current=10500, monthly=500):
        pa = _FakePortfolioAccount(lot_factor)
        acc = _FakeAccount()
        return {
            "portfolio_account": pa,
            "account": acc,
            "starting_balance": starting,
            "current_balance": current,
            "monthly_profit": monthly,
        }

    def test_modere_single_account(self):
        data = self._make_data(lot_factor=1.0, monthly=1000)
        detail = _FakeDetail([_FakePortfolioAccount(1.0)])
        result = calculate_standard_preview("Modere", [data], detail)
        assert result["withdrawal_percentage"] == 80.0
        assert result["total_suggested_withdrawal"] == 800.0
        assert len(result["accounts"]) == 1
        assert result["accounts"][0]["weight"] == pytest.approx(1.0)

    def test_agressif_withdrawal(self):
        data = self._make_data(lot_factor=2.5, monthly=2000)
        detail = _FakeDetail([_FakePortfolioAccount(2.5)])
        result = calculate_standard_preview("Agressif", [data], detail)
        assert result["withdrawal_percentage"] == 90.0
        assert result["total_suggested_withdrawal"] == 1800.0

    def test_zero_profit_no_withdrawal(self):
        data = self._make_data(monthly=0)
        detail = _FakeDetail([_FakePortfolioAccount(1.0)])
        result = calculate_standard_preview("Modere", [data], detail)
        assert result["total_suggested_withdrawal"] == 0

    def test_negative_profit_no_withdrawal(self):
        data = self._make_data(monthly=-500)
        detail = _FakeDetail([_FakePortfolioAccount(1.0)])
        result = calculate_standard_preview("Modere", [data], detail)
        assert result["total_suggested_withdrawal"] == 0

    def test_weight_calculation_two_accounts(self):
        pa1 = _FakePortfolioAccount(1.0)
        pa2 = _FakePortfolioAccount(3.0)
        detail = _FakeDetail([pa1, pa2])
        data1 = {
            "portfolio_account": pa1,
            "account": _FakeAccount(id=1),
            "starting_balance": 10000,
            "current_balance": 10500,
            "monthly_profit": 500,
        }
        data2 = {
            "portfolio_account": pa2,
            "account": _FakeAccount(id=2),
            "starting_balance": 30000,
            "current_balance": 31500,
            "monthly_profit": 1500,
        }
        result = calculate_standard_preview("Modere", [data1, data2], detail)
        assert result["accounts"][0]["weight"] == pytest.approx(0.25)
        assert result["accounts"][1]["weight"] == pytest.approx(0.75)

    def test_profit_percent_calculation(self):
        data = self._make_data(starting=10000, monthly=500)
        detail = _FakeDetail([_FakePortfolioAccount(1.0)])
        result = calculate_standard_preview("Modere", [data], detail)
        assert result["accounts"][0]["profit_percent"] == pytest.approx(5.0)

    def test_zero_starting_balance_no_divide_error(self):
        data = self._make_data(starting=0, monthly=100)
        detail = _FakeDetail([_FakePortfolioAccount(1.0)])
        result = calculate_standard_preview("Modere", [data], detail)
        assert result["accounts"][0]["profit_percent"] == 0
