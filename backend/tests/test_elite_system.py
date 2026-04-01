"""Tests for Elite Trading Level System"""
import pytest
from services.portfolio.elite_system import (
    get_phase,
    get_level_from_lot_factor,
    calculate_distribution,
    ELITE_DISTRIBUTION,
)


# --- get_phase() ---

class TestGetPhase:
    def test_zero_capital_returns_phase_1(self):
        assert get_phase(0) == 1

    def test_below_5k_returns_phase_1(self):
        assert get_phase(4999) == 1

    def test_exactly_5k_returns_phase_2(self):
        assert get_phase(5000) == 2

    def test_below_25k_returns_phase_2(self):
        assert get_phase(24999) == 2

    def test_exactly_25k_returns_phase_3(self):
        assert get_phase(25000) == 3

    def test_exactly_100k_returns_phase_4(self):
        assert get_phase(100000) == 4

    def test_exactly_500k_returns_phase_5(self):
        assert get_phase(500000) == 5

    def test_above_500k_returns_phase_5(self):
        assert get_phase(1_000_000) == 5

    def test_negative_capital_returns_phase_1(self):
        assert get_phase(-100) == 1


# --- get_level_from_lot_factor() ---

class TestGetLevelFromLotFactor:
    def test_factor_0_2_returns_N1(self):
        assert get_level_from_lot_factor(0.2) == "N1"

    def test_factor_0_6_returns_N2(self):
        assert get_level_from_lot_factor(0.6) == "N2"

    def test_factor_1_0_returns_N3(self):
        assert get_level_from_lot_factor(1.0) == "N3"

    def test_factor_1_4_returns_N4(self):
        assert get_level_from_lot_factor(1.4) == "N4"

    def test_factor_1_8_returns_N5(self):
        assert get_level_from_lot_factor(1.8) == "N5"

    def test_unknown_factor_defaults_to_N3(self):
        assert get_level_from_lot_factor(2.5) == "N3"

    def test_zero_factor_defaults_to_N3(self):
        assert get_level_from_lot_factor(0) == "N3"


# --- calculate_distribution() ---

class TestCalculateDistribution:
    def test_phase1_N3_positive_profit(self):
        result = calculate_distribution(1, "N3", 1000)
        assert result["remuneration"] == pytest.approx(0)
        assert result["compound"] == pytest.approx(800)
        assert result["transfer"] == pytest.approx(200)
        assert result["remuneration_pct"] == 0.00
        assert result["compound_pct"] == 0.80
        assert result["transfer_pct"] == 0.20

    def test_phase5_N5_positive_profit(self):
        result = calculate_distribution(5, "N5", 1000)
        assert result["remuneration"] == pytest.approx(450)
        assert result["compound"] == pytest.approx(250)
        assert result["transfer"] == pytest.approx(300)

    def test_profit_zero_returns_zero_amounts(self):
        result = calculate_distribution(3, "N3", 0)
        assert result["remuneration"] == 0
        assert result["compound"] == 0
        assert result["transfer"] == 0
        # Percentages are still provided
        assert result["remuneration_pct"] == 0.15

    def test_negative_profit_returns_zero_amounts(self):
        result = calculate_distribution(2, "N4", -500)
        assert result["remuneration"] == 0
        assert result["compound"] == 0
        assert result["transfer"] == 0

    def test_invalid_phase_falls_back_to_phase1(self):
        result = calculate_distribution(99, "N3", 1000)
        # Should fallback to phase 1 distribution
        assert result["compound_pct"] == 0.80

    def test_invalid_level_falls_back_to_default(self):
        result = calculate_distribution(1, "INVALID", 1000)
        # Fallback is [0, 1, 0]
        assert result["compound"] == pytest.approx(1000)
        assert result["remuneration"] == pytest.approx(0)
        assert result["transfer"] == pytest.approx(0)

    def test_distribution_sums_to_one(self):
        """All distribution percentages should sum to 1.0 for every phase/level"""
        for phase, levels in ELITE_DISTRIBUTION.items():
            for level, dist in levels.items():
                total = sum(dist)
                assert total == pytest.approx(1.0), f"Phase {phase}, Level {level}: sum={total}"
