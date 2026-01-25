"""Alert service - monitors conditions and triggers alerts"""
from typing import Optional
from datetime import datetime
from db.repositories.alerts import alerts_repo
from models import Alert, AlertHistory
from config.alerts import AlertType, AlertCondition, AlertStatus
from config.logging import logger


class AlertService:
    """Service for checking and triggering alerts"""

    def __init__(self):
        pass

    def check_condition(self, condition: str, value: float, threshold: float) -> bool:
        """Check if a condition is met"""
        if condition == AlertCondition.ABOVE:
            return value > threshold
        elif condition == AlertCondition.BELOW:
            return value < threshold
        elif condition == AlertCondition.EQUALS:
            return abs(value - threshold) < 0.01  # Allow small tolerance
        return False

    def check_alerts_for_account(self, account_id: int, metrics: dict) -> list[AlertHistory]:
        """Check all active alerts for an account and trigger if conditions are met

        Args:
            account_id: The account ID to check
            metrics: Dict with current metrics (drawdown, profit, balance, equity, margin_level)

        Returns:
            List of triggered alerts
        """
        triggered = []
        alerts = alerts_repo.get_alerts(account_id=account_id, status=AlertStatus.ACTIVE)

        for alert in alerts:
            value = self._get_metric_value(alert.alert_type, metrics)
            if value is None:
                continue

            if self.check_condition(alert.condition, value, alert.threshold):
                message = self._format_alert_message(alert, value)
                if alerts_repo.trigger_alert(alert.id, value, message):
                    triggered.append(AlertHistory(
                        id=0,  # Will be set by DB
                        alert_id=alert.id,
                        account_id=account_id,
                        alert_type=alert.alert_type,
                        threshold=alert.threshold,
                        actual_value=value,
                        message=message,
                        triggered_at=datetime.now()
                    ))
                    logger.info("Alert triggered",
                              alert_id=alert.id,
                              account_id=account_id,
                              alert_type=alert.alert_type,
                              threshold=alert.threshold,
                              actual_value=value)

        return triggered

    def _get_metric_value(self, alert_type: str, metrics: dict) -> Optional[float]:
        """Get the metric value for a given alert type"""
        mapping = {
            AlertType.DRAWDOWN: "drawdown_percent",
            AlertType.PROFIT: "profit",
            AlertType.LOSS: "profit",  # Negative profit
            AlertType.BALANCE: "balance",
            AlertType.EQUITY: "equity",
            AlertType.MARGIN_LEVEL: "margin_level",
        }
        key = mapping.get(alert_type)
        return metrics.get(key) if key else None

    def _format_alert_message(self, alert: Alert, value: float) -> str:
        """Format a human-readable alert message"""
        type_labels = {
            AlertType.DRAWDOWN: "Drawdown",
            AlertType.PROFIT: "Profit",
            AlertType.LOSS: "Loss",
            AlertType.BALANCE: "Balance",
            AlertType.EQUITY: "Equity",
            AlertType.MARGIN_LEVEL: "Margin Level",
        }
        condition_labels = {
            AlertCondition.ABOVE: "exceeded",
            AlertCondition.BELOW: "dropped below",
            AlertCondition.EQUALS: "reached",
        }

        type_label = type_labels.get(alert.alert_type, alert.alert_type)
        condition_label = condition_labels.get(alert.condition, alert.condition)

        if alert.message:
            return alert.message

        if alert.alert_type in [AlertType.DRAWDOWN, AlertType.MARGIN_LEVEL]:
            return f"{type_label} {condition_label} {alert.threshold}% (current: {value:.2f}%)"
        else:
            return f"{type_label} {condition_label} {alert.threshold:.2f} (current: {value:.2f})"

    # CRUD operations delegated to repository
    def create_alert(self, alert: Alert) -> Optional[int]:
        """Create a new alert"""
        return alerts_repo.create_alert(alert)

    def get_alerts(self, account_id: Optional[int] = None, status: Optional[str] = None) -> list[Alert]:
        """Get alerts"""
        return alerts_repo.get_alerts(account_id, status)

    def get_alert(self, alert_id: int) -> Optional[Alert]:
        """Get a specific alert"""
        return alerts_repo.get_alert(alert_id)

    def update_alert(self, alert_id: int, **kwargs) -> bool:
        """Update an alert"""
        return alerts_repo.update_alert(alert_id, **kwargs)

    def delete_alert(self, alert_id: int) -> bool:
        """Delete an alert"""
        return alerts_repo.delete_alert(alert_id)

    def get_alert_history(self, account_id: Optional[int] = None, limit: int = 100) -> list[AlertHistory]:
        """Get alert history"""
        return alerts_repo.get_alert_history(account_id, limit)

    def reset_alert(self, alert_id: int) -> bool:
        """Reset a triggered alert back to active status"""
        return alerts_repo.update_alert(alert_id, status=AlertStatus.ACTIVE)


# Global instance
alert_service = AlertService()
