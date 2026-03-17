"""Elite Trading Level System - Constants and calculations for Conservateur portfolios"""

# Mapping lot factor -> level
LOT_FACTOR_TO_LEVEL = {
    1.8: "N5",  # Highest risk
    1.4: "N4",
    1.0: "N3",
    0.6: "N2",
    0.2: "N1",  # Lowest risk
}

# Phase thresholds based on total capital
PHASE_THRESHOLDS = [0, 5000, 25000, 100000, 500000]  # Phase 1-5

# Distribution by phase and level: [remuneration, compound, transfer]
ELITE_DISTRIBUTION = {
    1: {  # Phase 1: Survie (0-5k)
        "N5": [0.10, 0.60, 0.30],
        "N4": [0.05, 0.70, 0.25],
        "N3": [0.00, 0.80, 0.20],
        "N2": [0.00, 0.90, 0.10],
        "N1": [0.00, 1.00, 0.00],
    },
    2: {  # Phase 2: Fondation (5k-25k)
        "N5": [0.15, 0.55, 0.30],
        "N4": [0.10, 0.65, 0.25],
        "N3": [0.05, 0.75, 0.20],
        "N2": [0.00, 0.85, 0.15],
        "N1": [0.00, 1.00, 0.00],
    },
    3: {  # Phase 3: Acceleration (25k-100k)
        "N5": [0.25, 0.45, 0.30],
        "N4": [0.20, 0.55, 0.25],
        "N3": [0.15, 0.65, 0.20],
        "N2": [0.10, 0.75, 0.15],
        "N1": [0.05, 0.95, 0.00],
    },
    4: {  # Phase 4: Securisation (100k-500k)
        "N5": [0.35, 0.35, 0.30],
        "N4": [0.30, 0.45, 0.25],
        "N3": [0.25, 0.55, 0.20],
        "N2": [0.20, 0.65, 0.15],
        "N1": [0.15, 0.85, 0.00],
    },
    5: {  # Phase 5: Patrimoine (500k+)
        "N5": [0.45, 0.25, 0.30],
        "N4": [0.35, 0.40, 0.25],
        "N3": [0.30, 0.70, 0.00],
        "N2": [0.25, 0.75, 0.00],
        "N1": [0.20, 0.80, 0.00],
    },
}

PHASE_NAMES = {
    1: "Survie",
    2: "Fondation",
    3: "Acceleration",
    4: "Securisation",
    5: "Patrimoine",
}


def get_phase(total_capital: float) -> int:
    """Get phase (1-5) based on total capital"""
    for i in range(4, -1, -1):
        if total_capital >= PHASE_THRESHOLDS[i]:
            return i + 1
    return 1


def get_level_from_lot_factor(lot_factor: float) -> str:
    """Map lot factor to Elite level (N5-N1)"""
    return LOT_FACTOR_TO_LEVEL.get(lot_factor, "N3")  # Default to N3


def calculate_distribution(phase: int, level: str, profit: float) -> dict:
    """Calculate Elite distribution for a given phase, level, and profit"""
    phase_dist = ELITE_DISTRIBUTION.get(phase, ELITE_DISTRIBUTION[1])
    dist = phase_dist.get(level, [0, 1, 0])
    remun_pct, compound_pct, transfer_pct = dist

    if profit > 0:
        return {
            "remuneration": profit * remun_pct,
            "compound": profit * compound_pct,
            "transfer": profit * transfer_pct,
            "remuneration_pct": remun_pct,
            "compound_pct": compound_pct,
            "transfer_pct": transfer_pct,
        }
    return {
        "remuneration": 0, "compound": 0, "transfer": 0,
        "remuneration_pct": remun_pct, "compound_pct": compound_pct, "transfer_pct": transfer_pct,
    }
