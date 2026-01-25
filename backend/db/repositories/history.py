"""History repository - stores balance/equity history points"""
from datetime import datetime, timedelta
from typing import Optional
from ..connection import get_connection
from models import HistoryPoint


class HistoryDatabase:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS history (
                        id SERIAL PRIMARY KEY,
                        account_id INTEGER NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        balance REAL NOT NULL,
                        equity REAL NOT NULL,
                        drawdown REAL NOT NULL,
                        drawdown_percent REAL NOT NULL,
                        UNIQUE(account_id, timestamp)
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_history_account_timestamp ON history(account_id, timestamp)")

    def save_point(self, point: HistoryPoint, account_id: int) -> bool:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO history (account_id, timestamp, balance, equity, drawdown, drawdown_percent)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (account_id, timestamp) DO UPDATE SET
                            balance = EXCLUDED.balance,
                            equity = EXCLUDED.equity,
                            drawdown = EXCLUDED.drawdown,
                            drawdown_percent = EXCLUDED.drawdown_percent
                    """, (
                        account_id,
                        point.timestamp,
                        point.balance,
                        point.equity,
                        point.drawdown,
                        point.drawdown_percent
                    ))
            return True
        except Exception as e:
            print(f"Error saving history point: {e}")
            return False

    def load_history(self, account_id: int, days: Optional[int] = None) -> list[HistoryPoint]:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    if days:
                        cutoff = datetime.now() - timedelta(days=days)
                        cur.execute("""
                            SELECT timestamp, balance, equity, drawdown, drawdown_percent
                            FROM history
                            WHERE account_id = %s AND timestamp >= %s
                            ORDER BY timestamp ASC
                        """, (account_id, cutoff))
                    else:
                        cur.execute("""
                            SELECT timestamp, balance, equity, drawdown, drawdown_percent
                            FROM history
                            WHERE account_id = %s
                            ORDER BY timestamp ASC
                        """, (account_id,))

                    return [
                        HistoryPoint(
                            timestamp=row[0],
                            balance=row[1],
                            equity=row[2],
                            drawdown=row[3],
                            drawdown_percent=row[4]
                        )
                        for row in cur.fetchall()
                    ]
        except Exception as e:
            print(f"Error loading history: {e}")
            return []

    def get_last_timestamp(self, account_id: int) -> Optional[datetime]:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT MAX(timestamp) FROM history WHERE account_id = %s", (account_id,))
                    result = cur.fetchone()[0]
                    return result
        except Exception:
            pass
        return None

    def cleanup_old_data(self, keep_days: int = 365):
        try:
            cutoff = datetime.now() - timedelta(days=keep_days)
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM history WHERE timestamp < %s", (cutoff,))
        except Exception as e:
            print(f"Error cleaning up old data: {e}")

    def get_stats(self, account_id: int = None) -> dict:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    if account_id:
                        cur.execute(
                            "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM history WHERE account_id = %s",
                            (account_id,)
                        )
                    else:
                        cur.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM history")
                    row = cur.fetchone()
                    return {
                        "count": row[0],
                        "first": row[1],
                        "last": row[2]
                    }
        except Exception:
            return {"count": 0, "first": None, "last": None}
