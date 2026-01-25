"""Balance history repository - stores balance snapshots for sparklines"""
from datetime import datetime, timedelta
from ..connection import get_connection
from models import AccountSummary
from config.logging import logger


class AccountBalanceHistory:
    """Historique des balances par compte pour les sparklines"""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS account_balance_history (
                        id SERIAL PRIMARY KEY,
                        account_id INTEGER NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        balance REAL NOT NULL,
                        equity REAL NOT NULL,
                        UNIQUE(account_id, timestamp)
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_balance_history_account ON account_balance_history(account_id, timestamp)")

    def save_snapshot(self, account_id: int, balance: float, equity: float) -> bool:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    now = datetime.now()
                    rounded = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
                    cur.execute("""
                        INSERT INTO account_balance_history (account_id, timestamp, balance, equity)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (account_id, timestamp) DO UPDATE SET
                            balance = EXCLUDED.balance,
                            equity = EXCLUDED.equity
                    """, (account_id, rounded, balance, equity))
            return True
        except Exception as e:
            logger.error("Error saving snapshot", account_id=account_id, error=str(e))
            return False

    def save_snapshot_at_time(self, account_id: int, balance: float, equity: float, timestamp: datetime) -> bool:
        """Sauvegarde un snapshot à un timestamp spécifique (pour rebuild depuis deals)"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # Arrondir au jour pour éviter les doublons
                    rounded = timestamp.replace(hour=12, minute=0, second=0, microsecond=0)
                    cur.execute("""
                        INSERT INTO account_balance_history (account_id, timestamp, balance, equity)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (account_id, timestamp) DO UPDATE SET
                            balance = EXCLUDED.balance,
                            equity = EXCLUDED.equity
                    """, (account_id, rounded, balance, equity))
            return True
        except Exception as e:
            logger.error("Error saving historical snapshot", account_id=account_id, error=str(e))
            return False

    def save_all_snapshots(self, accounts: list[AccountSummary]) -> bool:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    now = datetime.now()
                    rounded = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
                    for acc in accounts:
                        if acc.connected:
                            cur.execute("""
                                INSERT INTO account_balance_history (account_id, timestamp, balance, equity)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (account_id, timestamp) DO UPDATE SET
                                    balance = EXCLUDED.balance,
                                    equity = EXCLUDED.equity
                            """, (acc.id, rounded, acc.balance, acc.equity))
            return True
        except Exception as e:
            logger.error("Error saving snapshots", error=str(e))
            return False

    def get_history(self, account_id: int, days: int = 30) -> list[dict]:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cutoff = datetime.now() - timedelta(days=days)
                    cur.execute("""
                        SELECT timestamp, balance, equity
                        FROM account_balance_history
                        WHERE account_id = %s AND timestamp >= %s
                        ORDER BY timestamp ASC
                    """, (account_id, cutoff))
                    return [
                        {"timestamp": row[0].isoformat(), "balance": row[1], "equity": row[2]}
                        for row in cur.fetchall()
                    ]
        except Exception as e:
            logger.error("Error loading account history", account_id=account_id, error=str(e))
            return []

    def get_all_accounts_history(self, days: int = 30) -> dict[int, list[dict]]:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cutoff = datetime.now() - timedelta(days=days)
                    cur.execute("""
                        SELECT account_id, timestamp, balance, equity
                        FROM account_balance_history
                        WHERE timestamp >= %s
                        ORDER BY account_id, timestamp ASC
                    """, (cutoff,))

                    result: dict[int, list[dict]] = {}
                    for row in cur.fetchall():
                        account_id = row[0]
                        if account_id not in result:
                            result[account_id] = []
                        result[account_id].append({
                            "timestamp": row[1].isoformat(),
                            "balance": row[2],
                            "equity": row[3]
                        })
                    return result
        except Exception as e:
            logger.error("Error loading histories", error=str(e))
            return {}

    def get_sparkline_data(self, account_id: int, points: int = 20) -> list[float]:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT balance
                        FROM account_balance_history
                        WHERE account_id = %s
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, (account_id, points))
                    return [row[0] for row in cur.fetchall()][::-1]
        except Exception as e:
            logger.error("Error getting sparkline", account_id=account_id, error=str(e))
            return []

    def get_all_sparklines(self, points: int = 20) -> dict[int, list[float]]:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT DISTINCT account_id FROM account_balance_history")
                    account_ids = [row[0] for row in cur.fetchall()]

                    result: dict[int, list[float]] = {}
                    for acc_id in account_ids:
                        cur.execute("""
                            SELECT balance
                            FROM account_balance_history
                            WHERE account_id = %s
                            ORDER BY timestamp DESC
                            LIMIT %s
                        """, (acc_id, points))
                        result[acc_id] = [row[0] for row in cur.fetchall()][::-1]
                    return result
        except Exception as e:
            logger.error("Error loading sparklines", error=str(e))
            return {}

    def cleanup_old_data(self, keep_days: int = 90):
        try:
            cutoff = datetime.now() - timedelta(days=keep_days)
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM account_balance_history WHERE timestamp < %s", (cutoff,))
        except Exception as e:
            logger.error("Error cleaning up data", error=str(e))
