"""Alert configuration and types"""
from enum import Enum


class AlertType(str, Enum):
    """Types of alerts"""
    DRAWDOWN = "drawdown"          # Drawdown exceeds threshold
    PROFIT = "profit"              # Profit reaches target
    LOSS = "loss"                  # Loss exceeds limit
    BALANCE = "balance"            # Balance threshold
    EQUITY = "equity"              # Equity threshold
    MARGIN_LEVEL = "margin_level"  # Margin level warning


class AlertCondition(str, Enum):
    """Alert trigger conditions"""
    ABOVE = "above"
    BELOW = "below"
    EQUALS = "equals"


class AlertStatus(str, Enum):
    """Alert status"""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    DISABLED = "disabled"


# Default alert thresholds
DEFAULT_ALERT_THRESHOLDS = {
    AlertType.DRAWDOWN: 10.0,     # 10% drawdown
    AlertType.MARGIN_LEVEL: 150.0, # 150% margin level
}
