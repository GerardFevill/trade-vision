"""Alerts repository - stores and manages alert configurations"""
from datetime import datetime
from typing import Optional
from ..connection import get_connection
from models import Alert, AlertHistory
from config.logging import logger


class AlertsRepository:
    """Repository for alert management"""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        """Initialize alerts tables"""
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Alerts configuration table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        id SERIAL PRIMARY KEY,
                        account_id INTEGER NOT NULL,
                        alert_type VARCHAR(50) NOT NULL,
                        condition VARCHAR(20) NOT NULL,
                        threshold REAL NOT NULL,
                        message TEXT,
                        status VARCHAR(20) DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        triggered_at TIMESTAMP,
                        UNIQUE(account_id, alert_type, condition, threshold)
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_account ON alerts(account_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)")

                # Alert history table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS alert_history (
                        id SERIAL PRIMARY KEY,
                        alert_id INTEGER REFERENCES alerts(id),
                        account_id INTEGER NOT NULL,
                        alert_type VARCHAR(50) NOT NULL,
                        threshold REAL NOT NULL,
                        actual_value REAL NOT NULL,
                        message TEXT NOT NULL,
                        triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_alert_history_account ON alert_history(account_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_alert_history_time ON alert_history(triggered_at)")

    def create_alert(self, alert: Alert) -> Optional[int]:
        """Create a new alert configuration"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO alerts (account_id, alert_type, condition, threshold, message, status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (account_id, alert_type, condition, threshold) DO UPDATE
                        SET message = EXCLUDED.message, status = EXCLUDED.status
                        RETURNING id
                    """, (
                        alert.account_id,
                        alert.alert_type,
                        alert.condition,
                        alert.threshold,
                        alert.message,
                        alert.status
                    ))
                    result = cur.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logger.error("Error creating alert", error=str(e))
            return None

    def get_alerts(self, account_id: Optional[int] = None, status: Optional[str] = None) -> list[Alert]:
        """Get alerts, optionally filtered by account and status"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    query = "SELECT id, account_id, alert_type, condition, threshold, message, status, created_at, triggered_at FROM alerts WHERE 1=1"
                    params = []

                    if account_id:
                        query += " AND account_id = %s"
                        params.append(account_id)
                    if status:
                        query += " AND status = %s"
                        params.append(status)

                    query += " ORDER BY created_at DESC"
                    cur.execute(query, params)

                    alerts = []
                    for row in cur.fetchall():
                        alerts.append(Alert(
                            id=row[0],
                            account_id=row[1],
                            alert_type=row[2],
                            condition=row[3],
                            threshold=row[4],
                            message=row[5],
                            status=row[6],
                            created_at=row[7],
                            triggered_at=row[8]
                        ))
                    return alerts
        except Exception as e:
            logger.error("Error getting alerts", error=str(e))
            return []

    def get_alert(self, alert_id: int) -> Optional[Alert]:
        """Get a specific alert by ID"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, account_id, alert_type, condition, threshold, message, status, created_at, triggered_at
                        FROM alerts WHERE id = %s
                    """, (alert_id,))
                    row = cur.fetchone()
                    if row:
                        return Alert(
                            id=row[0],
                            account_id=row[1],
                            alert_type=row[2],
                            condition=row[3],
                            threshold=row[4],
                            message=row[5],
                            status=row[6],
                            created_at=row[7],
                            triggered_at=row[8]
                        )
        except Exception as e:
            logger.error("Error getting alert", alert_id=alert_id, error=str(e))
        return None

    def update_alert(self, alert_id: int, **kwargs) -> bool:
        """Update an alert's properties"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    updates = []
                    values = []
                    for key, value in kwargs.items():
                        if key in ['threshold', 'message', 'status', 'condition']:
                            updates.append(f"{key} = %s")
                            values.append(value)

                    if not updates:
                        return False

                    values.append(alert_id)
                    cur.execute(f"""
                        UPDATE alerts SET {', '.join(updates)} WHERE id = %s
                    """, values)
                    return cur.rowcount > 0
        except Exception as e:
            logger.error("Error updating alert", alert_id=alert_id, error=str(e))
            return False

    def delete_alert(self, alert_id: int) -> bool:
        """Delete an alert"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM alerts WHERE id = %s", (alert_id,))
                    return cur.rowcount > 0
        except Exception as e:
            logger.error("Error deleting alert", alert_id=alert_id, error=str(e))
            return False

    def trigger_alert(self, alert_id: int, actual_value: float, message: str) -> bool:
        """Mark an alert as triggered and record in history"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # Get alert details
                    cur.execute("""
                        SELECT account_id, alert_type, threshold FROM alerts WHERE id = %s
                    """, (alert_id,))
                    row = cur.fetchone()
                    if not row:
                        return False

                    account_id, alert_type, threshold = row

                    # Update alert status
                    cur.execute("""
                        UPDATE alerts SET status = 'triggered', triggered_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (alert_id,))

                    # Record in history
                    cur.execute("""
                        INSERT INTO alert_history (alert_id, account_id, alert_type, threshold, actual_value, message)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (alert_id, account_id, alert_type, threshold, actual_value, message))

                    return True
        except Exception as e:
            logger.error("Error triggering alert", alert_id=alert_id, error=str(e))
            return False

    def get_alert_history(self, account_id: Optional[int] = None, limit: int = 100) -> list[AlertHistory]:
        """Get alert history"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT id, alert_id, account_id, alert_type, threshold, actual_value, message, triggered_at
                        FROM alert_history
                    """
                    params = []

                    if account_id:
                        query += " WHERE account_id = %s"
                        params.append(account_id)

                    query += " ORDER BY triggered_at DESC LIMIT %s"
                    params.append(limit)

                    cur.execute(query, params)

                    history = []
                    for row in cur.fetchall():
                        history.append(AlertHistory(
                            id=row[0],
                            alert_id=row[1],
                            account_id=row[2],
                            alert_type=row[3],
                            threshold=row[4],
                            actual_value=row[5],
                            message=row[6],
                            triggered_at=row[7]
                        ))
                    return history
        except Exception as e:
            logger.error("Error getting alert history", error=str(e))
            return []


# Global instance
alerts_repo = AlertsRepository()
