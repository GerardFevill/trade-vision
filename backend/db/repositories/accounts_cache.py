"""Accounts cache repository - caches account summaries"""
from datetime import datetime
from typing import Optional
from ..connection import get_connection
from models import AccountSummary
from config.logging import logger


class AccountsCache:
    """Cache PostgreSQL pour les résumés de comptes MT5"""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS accounts_cache (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        broker TEXT,
                        server TEXT,
                        balance REAL,
                        equity REAL,
                        profit REAL,
                        profit_percent REAL,
                        drawdown REAL,
                        trades INTEGER,
                        win_rate REAL,
                        currency TEXT,
                        leverage INTEGER,
                        connected BOOLEAN,
                        client TEXT,
                        updated_at TIMESTAMP NOT NULL
                    )
                """)
                # Migration: rename profile to client if needed
                cur.execute("""
                    DO $$
                    BEGIN
                        IF EXISTS (SELECT 1 FROM information_schema.columns
                                   WHERE table_name='accounts_cache' AND column_name='profile') THEN
                            ALTER TABLE accounts_cache RENAME COLUMN profile TO client;
                        END IF;
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                                       WHERE table_name='accounts_cache' AND column_name='client') THEN
                            ALTER TABLE accounts_cache ADD COLUMN client TEXT;
                        END IF;
                    END $$;
                """)

    def save_accounts(self, accounts: list[AccountSummary]) -> bool:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    now = datetime.now()
                    for acc in accounts:
                        cur.execute("""
                            INSERT INTO accounts_cache
                            (id, name, broker, server, balance, equity, profit, profit_percent,
                             drawdown, trades, win_rate, currency, leverage, connected, client, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE SET
                                name = EXCLUDED.name,
                                broker = EXCLUDED.broker,
                                server = EXCLUDED.server,
                                balance = EXCLUDED.balance,
                                equity = EXCLUDED.equity,
                                profit = EXCLUDED.profit,
                                profit_percent = EXCLUDED.profit_percent,
                                drawdown = EXCLUDED.drawdown,
                                trades = EXCLUDED.trades,
                                win_rate = EXCLUDED.win_rate,
                                currency = EXCLUDED.currency,
                                leverage = EXCLUDED.leverage,
                                connected = EXCLUDED.connected,
                                client = EXCLUDED.client,
                                updated_at = EXCLUDED.updated_at
                        """, (
                            acc.id, acc.name, acc.broker, acc.server,
                            acc.balance, acc.equity, acc.profit, acc.profit_percent,
                            acc.drawdown, acc.trades, acc.win_rate,
                            acc.currency, acc.leverage, acc.connected, acc.client, now
                        ))
            return True
        except Exception as e:
            logger.error("Error saving accounts cache", error=str(e))
            return False

    def load_accounts(self) -> list[AccountSummary]:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, name, broker, server, balance, equity, profit, profit_percent,
                               drawdown, trades, win_rate, currency, leverage, connected, client
                        FROM accounts_cache
                        ORDER BY id
                    """)
                    return [
                        AccountSummary(
                            id=row[0], name=row[1], broker=row[2], server=row[3],
                            balance=row[4], equity=row[5], profit=row[6], profit_percent=row[7],
                            drawdown=row[8], trades=row[9], win_rate=row[10],
                            currency=row[11], leverage=row[12], connected=row[13], client=row[14]
                        )
                        for row in cur.fetchall()
                    ]
        except Exception as e:
            logger.error("Error loading accounts cache", error=str(e))
            return []

    def get_last_update(self) -> Optional[datetime]:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT MAX(updated_at) FROM accounts_cache")
                    return cur.fetchone()[0]
        except Exception:
            pass
        return None

    def is_cache_valid(self, max_age_seconds: int = 60) -> bool:
        last_update = self.get_last_update()
        if not last_update:
            return False
        age = (datetime.now() - last_update).total_seconds()
        return age < max_age_seconds

    def update_account(self, account: AccountSummary) -> bool:
        """Met à jour un seul compte dans le cache"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    now = datetime.now()
                    cur.execute("""
                        INSERT INTO accounts_cache
                        (id, name, broker, server, balance, equity, profit, profit_percent,
                         drawdown, trades, win_rate, currency, leverage, connected, client, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            balance = EXCLUDED.balance,
                            equity = EXCLUDED.equity,
                            profit = EXCLUDED.profit,
                            profit_percent = EXCLUDED.profit_percent,
                            drawdown = EXCLUDED.drawdown,
                            trades = EXCLUDED.trades,
                            win_rate = EXCLUDED.win_rate,
                            connected = EXCLUDED.connected,
                            updated_at = EXCLUDED.updated_at
                    """, (
                        account.id, account.name, account.broker, account.server,
                        account.balance, account.equity, account.profit, account.profit_percent,
                        account.drawdown, account.trades, account.win_rate,
                        account.currency, account.leverage, account.connected, account.client, now
                    ))
            return True
        except Exception as e:
            logger.error("Error updating account cache", error=str(e))
            return False
