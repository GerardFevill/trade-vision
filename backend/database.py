import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from models import HistoryPoint


class HistoryDatabase:
    def __init__(self, db_path: str = "mt5_history.db"):
        self.db_path = Path(__file__).parent / db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL UNIQUE,
                    balance REAL NOT NULL,
                    equity REAL NOT NULL,
                    drawdown REAL NOT NULL,
                    drawdown_percent REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON history(timestamp)")
            conn.commit()

    def save_point(self, point: HistoryPoint) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO history (timestamp, balance, equity, drawdown, drawdown_percent)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    point.timestamp.isoformat(),
                    point.balance,
                    point.equity,
                    point.drawdown,
                    point.drawdown_percent
                ))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error saving history point: {e}")
            return False

    def load_history(self, days: Optional[int] = None) -> list[HistoryPoint]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                if days:
                    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                    cursor = conn.execute("""
                        SELECT timestamp, balance, equity, drawdown, drawdown_percent
                        FROM history
                        WHERE timestamp >= ?
                        ORDER BY timestamp ASC
                    """, (cutoff,))
                else:
                    cursor = conn.execute("""
                        SELECT timestamp, balance, equity, drawdown, drawdown_percent
                        FROM history
                        ORDER BY timestamp ASC
                    """)

                points = []
                for row in cursor.fetchall():
                    points.append(HistoryPoint(
                        timestamp=datetime.fromisoformat(row[0]),
                        balance=row[1],
                        equity=row[2],
                        drawdown=row[3],
                        drawdown_percent=row[4]
                    ))
                return points
        except Exception as e:
            print(f"Error loading history: {e}")
            return []

    def get_last_timestamp(self) -> Optional[datetime]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT MAX(timestamp) FROM history")
                result = cursor.fetchone()[0]
                if result:
                    return datetime.fromisoformat(result)
        except Exception:
            pass
        return None

    def cleanup_old_data(self, keep_days: int = 365):
        """Supprime les données plus anciennes que keep_days"""
        try:
            cutoff = (datetime.now() - timedelta(days=keep_days)).isoformat()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM history WHERE timestamp < ?", (cutoff,))
                conn.commit()
        except Exception as e:
            print(f"Error cleaning up old data: {e}")

    def get_stats(self) -> dict:
        """Retourne des stats sur la base de données"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM history")
                row = cursor.fetchone()
                return {
                    "count": row[0],
                    "first": row[1],
                    "last": row[2]
                }
        except Exception:
            return {"count": 0, "first": None, "last": None}


# Instance globale
history_db = HistoryDatabase()
