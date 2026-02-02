"""Portfolio repository - manages portfolios and their accounts"""
from datetime import datetime
from typing import Optional
from ..connection import get_connection
from models import (
    Portefeuille, PortefeuilleAccount, PORTFOLIO_TYPES,
    PortefeuilleSummary, PortefeuilleDetail, PortefeuilleAccountDetail, AccountSummary
)
from config.logging import logger
from .balance_history import AccountBalanceHistory


class PortefeuilleRepository:
    """Repository for portfolio management"""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Main portfolios table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS portefeuilles (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        client TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """)

                # Portfolio-Account association table with lot factor
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS portefeuille_accounts (
                        portfolio_id INTEGER REFERENCES portefeuilles(id) ON DELETE CASCADE,
                        account_id INTEGER NOT NULL,
                        lot_factor REAL NOT NULL,
                        PRIMARY KEY (portfolio_id, account_id)
                    )
                """)

                # Index for faster lookups by client
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_portefeuilles_client
                    ON portefeuilles(client)
                """)

                # Monthly records table for tracking withdrawals and gains
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS portefeuille_monthly_records (
                        id SERIAL PRIMARY KEY,
                        portfolio_id INTEGER REFERENCES portefeuilles(id) ON DELETE CASCADE,
                        account_id INTEGER NOT NULL,
                        month VARCHAR(7) NOT NULL,
                        lot_factor REAL NOT NULL,
                        starting_balance REAL NOT NULL DEFAULT 0,
                        ending_balance REAL NOT NULL DEFAULT 0,
                        profit REAL NOT NULL DEFAULT 0,
                        withdrawal REAL NOT NULL DEFAULT 0,
                        note TEXT,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        UNIQUE (portfolio_id, account_id, month)
                    )
                """)

                # Add Elite columns if they don't exist
                cur.execute("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                                       WHERE table_name='portefeuille_monthly_records' AND column_name='remuneration') THEN
                            ALTER TABLE portefeuille_monthly_records ADD COLUMN remuneration REAL DEFAULT 0;
                        END IF;
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                                       WHERE table_name='portefeuille_monthly_records' AND column_name='compound') THEN
                            ALTER TABLE portefeuille_monthly_records ADD COLUMN compound REAL DEFAULT 0;
                        END IF;
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                                       WHERE table_name='portefeuille_monthly_records' AND column_name='transfer_amount') THEN
                            ALTER TABLE portefeuille_monthly_records ADD COLUMN transfer_amount REAL DEFAULT 0;
                        END IF;
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                                       WHERE table_name='portefeuille_monthly_records' AND column_name='level') THEN
                            ALTER TABLE portefeuille_monthly_records ADD COLUMN level VARCHAR(5);
                        END IF;
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                                       WHERE table_name='portefeuille_monthly_records' AND column_name='is_closed') THEN
                            ALTER TABLE portefeuille_monthly_records ADD COLUMN is_closed BOOLEAN DEFAULT FALSE;
                        END IF;
                    END $$;
                """)

                # Index for faster monthly lookups
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_monthly_records_month
                    ON portefeuille_monthly_records(portfolio_id, month)
                """)

    # CRUD Operations for Portfolios

    def create_portfolio(self, name: str, type: str, client: str) -> Optional[Portefeuille]:
        """Create a new portfolio"""
        if type not in PORTFOLIO_TYPES:
            logger.error("Invalid portfolio type", type=type)
            return None

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    now = datetime.now()
                    cur.execute("""
                        INSERT INTO portefeuilles (name, type, client, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                    """, (name, type, client, now, now))
                    portfolio_id = cur.fetchone()[0]

                    return Portefeuille(
                        id=portfolio_id,
                        name=name,
                        type=type,
                        client=client,
                        created_at=now,
                        updated_at=now
                    )
        except Exception as e:
            logger.error("Error creating portfolio", error=str(e))
            return None

    def get_portfolio(self, portfolio_id: int) -> Optional[Portefeuille]:
        """Get a portfolio by ID"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, name, type, client, created_at, updated_at
                        FROM portefeuilles
                        WHERE id = %s
                    """, (portfolio_id,))
                    row = cur.fetchone()
                    if row:
                        return Portefeuille(
                            id=row[0], name=row[1], type=row[2],
                            client=row[3], created_at=row[4], updated_at=row[5]
                        )
        except Exception as e:
            logger.error("Error getting portfolio", error=str(e))
        return None

    def list_portfolios(self, client: Optional[str] = None) -> list[PortefeuilleSummary]:
        """List all portfolios, optionally filtered by client"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    if client:
                        cur.execute("""
                            SELECT p.id, p.name, p.type, p.client, p.created_at, p.updated_at,
                                   COALESCE(SUM(ac.balance), 0) as total_balance,
                                   COALESCE(SUM(ac.profit), 0) as total_profit,
                                   COUNT(pa.account_id) as account_count
                            FROM portefeuilles p
                            LEFT JOIN portefeuille_accounts pa ON p.id = pa.portfolio_id
                            LEFT JOIN accounts_cache ac ON pa.account_id = ac.id
                            WHERE p.client = %s
                            GROUP BY p.id, p.name, p.type, p.client, p.created_at, p.updated_at
                            ORDER BY p.id
                        """, (client,))
                    else:
                        cur.execute("""
                            SELECT p.id, p.name, p.type, p.client, p.created_at, p.updated_at,
                                   COALESCE(SUM(ac.balance), 0) as total_balance,
                                   COALESCE(SUM(ac.profit), 0) as total_profit,
                                   COUNT(pa.account_id) as account_count
                            FROM portefeuilles p
                            LEFT JOIN portefeuille_accounts pa ON p.id = pa.portfolio_id
                            LEFT JOIN accounts_cache ac ON pa.account_id = ac.id
                            GROUP BY p.id, p.name, p.type, p.client, p.created_at, p.updated_at
                            ORDER BY p.id
                        """)

                    return [
                        PortefeuilleSummary(
                            id=row[0], name=row[1], type=row[2], client=row[3],
                            created_at=row[4].isoformat() if row[4] else "",
                            updated_at=row[5].isoformat() if row[5] else "",
                            total_balance=row[6] or 0,
                            total_profit=row[7] or 0,
                            account_count=row[8] or 0
                        )
                        for row in cur.fetchall()
                    ]
        except Exception as e:
            logger.error("Error listing portfolios", error=str(e))
            return []

    def update_portfolio(self, portfolio_id: int, name: Optional[str] = None,
                        type: Optional[str] = None) -> bool:
        """Update portfolio name and/or type"""
        if type and type not in PORTFOLIO_TYPES:
            logger.error("Invalid portfolio type", type=type)
            return False

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    updates = []
                    params = []

                    if name:
                        updates.append("name = %s")
                        params.append(name)
                    if type:
                        updates.append("type = %s")
                        params.append(type)

                    if not updates:
                        return True

                    updates.append("updated_at = %s")
                    params.append(datetime.now())
                    params.append(portfolio_id)

                    cur.execute(f"""
                        UPDATE portefeuilles
                        SET {', '.join(updates)}
                        WHERE id = %s
                    """, tuple(params))

                    return cur.rowcount > 0
        except Exception as e:
            logger.error("Error updating portfolio", error=str(e))
            return False

    def delete_portfolio(self, portfolio_id: int) -> bool:
        """Delete a portfolio and all its account associations"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM portefeuilles WHERE id = %s", (portfolio_id,))
                    return cur.rowcount > 0
        except Exception as e:
            logger.error("Error deleting portfolio", error=str(e))
            return False

    # Account association methods

    def add_account(self, portfolio_id: int, account_id: int, lot_factor: float) -> bool:
        """Add an account to a portfolio with a lot factor"""
        # Validate lot factor for this portfolio type
        portfolio = self.get_portfolio(portfolio_id)
        if not portfolio:
            logger.error("Portfolio not found", portfolio_id=portfolio_id)
            return False

        available_factors = PORTFOLIO_TYPES.get(portfolio.type, [])
        # Securise portfolios have no factor restrictions (empty list = unlimited accounts)
        if available_factors and lot_factor not in available_factors:
            logger.error("Invalid lot factor for portfolio type",
                        lot_factor=lot_factor, type=portfolio.type,
                        available=available_factors)
            return False

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO portefeuille_accounts (portfolio_id, account_id, lot_factor)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (portfolio_id, account_id) DO UPDATE SET
                            lot_factor = EXCLUDED.lot_factor
                    """, (portfolio_id, account_id, lot_factor))

                    # Update portfolio timestamp
                    cur.execute("""
                        UPDATE portefeuilles SET updated_at = %s WHERE id = %s
                    """, (datetime.now(), portfolio_id))

                    return True
        except Exception as e:
            logger.error("Error adding account to portfolio", error=str(e))
            return False

    def remove_account(self, portfolio_id: int, account_id: int) -> bool:
        """Remove an account from a portfolio"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        DELETE FROM portefeuille_accounts
                        WHERE portfolio_id = %s AND account_id = %s
                    """, (portfolio_id, account_id))

                    if cur.rowcount > 0:
                        cur.execute("""
                            UPDATE portefeuilles SET updated_at = %s WHERE id = %s
                        """, (datetime.now(), portfolio_id))

                    return cur.rowcount > 0
        except Exception as e:
            logger.error("Error removing account from portfolio", error=str(e))
            return False

    def get_portfolio_accounts(self, portfolio_id: int) -> list[PortefeuilleAccount]:
        """Get all accounts in a portfolio"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT portfolio_id, account_id, lot_factor
                        FROM portefeuille_accounts
                        WHERE portfolio_id = %s
                        ORDER BY lot_factor
                    """, (portfolio_id,))

                    return [
                        PortefeuilleAccount(
                            portfolio_id=row[0],
                            account_id=row[1],
                            lot_factor=row[2]
                        )
                        for row in cur.fetchall()
                    ]
        except Exception as e:
            logger.error("Error getting portfolio accounts", error=str(e))
            return []

    def get_portfolio_detail(self, portfolio_id: int) -> Optional[PortefeuilleDetail]:
        """Get detailed portfolio info with accounts and their data"""
        portfolio = self.get_portfolio(portfolio_id)
        if not portfolio:
            return None

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # Get accounts with their cached data
                    cur.execute("""
                        SELECT pa.account_id, pa.lot_factor,
                               ac.id, ac.name, ac.broker, ac.server, ac.balance, ac.equity,
                               ac.profit, ac.profit_percent, ac.drawdown, ac.trades, ac.win_rate,
                               ac.currency, ac.leverage, ac.connected, ac.client
                        FROM portefeuille_accounts pa
                        LEFT JOIN accounts_cache ac ON pa.account_id = ac.id
                        WHERE pa.portfolio_id = %s
                        ORDER BY pa.lot_factor
                    """, (portfolio_id,))

                    accounts = []
                    total_balance = 0.0
                    total_equity = 0.0
                    total_profit = 0.0

                    for row in cur.fetchall():
                        account_data = None
                        if row[2]:  # If account exists in cache
                            account_data = AccountSummary(
                                id=row[2], name=row[3], broker=row[4], server=row[5],
                                balance=row[6] or 0, equity=row[7] or 0, profit=row[8] or 0,
                                profit_percent=row[9] or 0, drawdown=row[10] or 0,
                                trades=row[11] or 0, win_rate=row[12] or 0,
                                currency=row[13] or "USD", leverage=row[14] or 0,
                                connected=row[15] or False, client=row[16]
                            )
                            total_balance += row[6] or 0
                            total_equity += row[7] or 0
                            total_profit += row[8] or 0

                        accounts.append(PortefeuilleAccountDetail(
                            account_id=row[0],
                            lot_factor=row[1],
                            account=account_data
                        ))

                    return PortefeuilleDetail(
                        id=portfolio.id,
                        name=portfolio.name,
                        type=portfolio.type,
                        client=portfolio.client,
                        total_balance=total_balance,
                        total_equity=total_equity,
                        total_profit=total_profit,
                        account_count=len(accounts),
                        accounts=accounts,
                        available_factors=PORTFOLIO_TYPES.get(portfolio.type, []),
                        created_at=portfolio.created_at.isoformat(),
                        updated_at=portfolio.updated_at.isoformat()
                    )
        except Exception as e:
            logger.error("Error getting portfolio detail", error=str(e))
            return None

    def get_clients(self) -> list[str]:
        """Get list of unique clients"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT client FROM portefeuilles ORDER BY client
                    """)
                    return [row[0] for row in cur.fetchall()]
        except Exception as e:
            logger.error("Error getting clients", error=str(e))
            return []

    def is_account_in_portfolio(self, account_id: int) -> Optional[int]:
        """Check if an account is already in a portfolio, returns portfolio_id or None"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT portfolio_id FROM portefeuille_accounts
                        WHERE account_id = %s
                    """, (account_id,))
                    row = cur.fetchone()
                    return row[0] if row else None
        except Exception as e:
            logger.error("Error checking account portfolio", error=str(e))
            return None

    def get_all_used_account_ids(self) -> list[int]:
        """Get all account IDs that are already in any portfolio"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT account_id FROM portefeuille_accounts
                    """)
                    return [row[0] for row in cur.fetchall()]
        except Exception as e:
            logger.error("Error getting used account IDs", error=str(e))
            return []

    # Monthly Records Methods

    def get_monthly_records(self, portfolio_id: int, month: Optional[str] = None) -> list[dict]:
        """Get monthly records for a portfolio, optionally filtered by month"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    if month:
                        cur.execute("""
                            SELECT pmr.id, pmr.portfolio_id, pmr.account_id, pmr.month,
                                   pmr.lot_factor, pmr.starting_balance, pmr.ending_balance,
                                   pmr.profit, pmr.withdrawal, pmr.note, pmr.created_at,
                                   ac.name, ac.currency
                            FROM portefeuille_monthly_records pmr
                            LEFT JOIN accounts_cache ac ON pmr.account_id = ac.id
                            WHERE pmr.portfolio_id = %s AND pmr.month = %s
                            ORDER BY pmr.lot_factor
                        """, (portfolio_id, month))
                    else:
                        cur.execute("""
                            SELECT pmr.id, pmr.portfolio_id, pmr.account_id, pmr.month,
                                   pmr.lot_factor, pmr.starting_balance, pmr.ending_balance,
                                   pmr.profit, pmr.withdrawal, pmr.note, pmr.created_at,
                                   ac.name, ac.currency
                            FROM portefeuille_monthly_records pmr
                            LEFT JOIN accounts_cache ac ON pmr.account_id = ac.id
                            WHERE pmr.portfolio_id = %s
                            ORDER BY pmr.month DESC, pmr.lot_factor
                        """, (portfolio_id,))

                    return [
                        {
                            "id": row[0],
                            "portfolio_id": row[1],
                            "account_id": row[2],
                            "month": row[3],
                            "lot_factor": row[4],
                            "starting_balance": row[5],
                            "ending_balance": row[6],
                            "profit": row[7],
                            "withdrawal": row[8],
                            "note": row[9],
                            "created_at": row[10],
                            "account_name": row[11] or f"Account #{row[2]}",
                            "currency": row[12] or "USD"
                        }
                        for row in cur.fetchall()
                    ]
        except Exception as e:
            logger.error("Error getting monthly records", error=str(e))
            return []

    def get_monthly_history(self, portfolio_id: int) -> list[str]:
        """Get list of months that have records for a portfolio"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT month FROM portefeuille_monthly_records
                        WHERE portfolio_id = %s
                        ORDER BY month DESC
                    """, (portfolio_id,))
                    return [row[0] for row in cur.fetchall()]
        except Exception as e:
            logger.error("Error getting monthly history", error=str(e))
            return []

    def create_monthly_snapshot(self, portfolio_id: int, month: str) -> bool:
        """Record starting balances for a month using historical balance data"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # Get current accounts with their current balances
                    cur.execute("""
                        SELECT pa.account_id, pa.lot_factor, ac.balance
                        FROM portefeuille_accounts pa
                        LEFT JOIN accounts_cache ac ON pa.account_id = ac.id
                        WHERE pa.portfolio_id = %s
                    """, (portfolio_id,))

                    accounts = cur.fetchall()
                    if not accounts:
                        return False

                    account_ids = [acc[0] for acc in accounts]

                    # Get historical balances at month start from balance_history
                    balance_history = AccountBalanceHistory()
                    historical_balances = balance_history.get_balances_at_month_start(account_ids, month)

                    now = datetime.now()
                    for acc in accounts:
                        account_id, lot_factor, current_balance = acc
                        current_balance = current_balance or 0

                        # Use historical balance if available, otherwise use current
                        starting_balance = historical_balances.get(account_id, current_balance)

                        # Record starting balance for the month
                        cur.execute("""
                            INSERT INTO portefeuille_monthly_records
                            (portfolio_id, account_id, month, lot_factor, starting_balance,
                             ending_balance, profit, withdrawal, created_at)
                            VALUES (%s, %s, %s, %s, %s, 0, 0, 0, %s)
                            ON CONFLICT (portfolio_id, account_id, month) DO NOTHING
                        """, (portfolio_id, account_id, month, lot_factor, starting_balance, now))

                    return True
        except Exception as e:
            logger.error("Error creating monthly snapshot", error=str(e))
            return False

    def close_monthly_snapshot(self, portfolio_id: int, month: str) -> bool:
        """Close a month by recording ending balances and calculating profit"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # Get current accounts with their balances
                    cur.execute("""
                        SELECT pa.account_id, ac.balance
                        FROM portefeuille_accounts pa
                        LEFT JOIN accounts_cache ac ON pa.account_id = ac.id
                        WHERE pa.portfolio_id = %s
                    """, (portfolio_id,))

                    accounts = {row[0]: row[1] or 0 for row in cur.fetchall()}
                    if not accounts:
                        return False

                    # Update each record with ending balance and profit
                    for account_id, ending_balance in accounts.items():
                        cur.execute("""
                            UPDATE portefeuille_monthly_records
                            SET ending_balance = %s,
                                profit = %s - starting_balance
                            WHERE portfolio_id = %s AND month = %s AND account_id = %s
                        """, (ending_balance, ending_balance, portfolio_id, month, account_id))

                    return True
        except Exception as e:
            logger.error("Error closing monthly snapshot", error=str(e))
            return False

    def update_withdrawal(self, portfolio_id: int, month: str, account_id: int,
                         withdrawal: float, note: Optional[str] = None) -> bool:
        """Update withdrawal amount for a specific account in a month"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    if note is not None:
                        cur.execute("""
                            UPDATE portefeuille_monthly_records
                            SET withdrawal = %s, note = %s
                            WHERE portfolio_id = %s AND month = %s AND account_id = %s
                        """, (withdrawal, note, portfolio_id, month, account_id))
                    else:
                        cur.execute("""
                            UPDATE portefeuille_monthly_records
                            SET withdrawal = %s
                            WHERE portfolio_id = %s AND month = %s AND account_id = %s
                        """, (withdrawal, portfolio_id, month, account_id))

                    return cur.rowcount > 0
        except Exception as e:
            logger.error("Error updating withdrawal", error=str(e))
            return False

    def update_starting_balance(self, portfolio_id: int, month: str,
                                account_id: int, starting_balance: float) -> bool:
        """Manually update starting balance for an account in a month"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # First ensure the record exists
                    cur.execute("""
                        INSERT INTO portefeuille_monthly_records
                        (portfolio_id, account_id, month, lot_factor, starting_balance,
                         ending_balance, profit, withdrawal, created_at)
                        SELECT %s, %s, %s, pa.lot_factor, %s, 0, 0, 0, NOW()
                        FROM portefeuille_accounts pa
                        WHERE pa.portfolio_id = %s AND pa.account_id = %s
                        ON CONFLICT (portfolio_id, account_id, month) DO UPDATE SET
                            starting_balance = EXCLUDED.starting_balance
                    """, (portfolio_id, account_id, month, starting_balance,
                          portfolio_id, account_id))
                    return cur.rowcount > 0
        except Exception as e:
            logger.error("Error updating starting balance", error=str(e))
            return False

    def calculate_distribution(self, portfolio_id: int, month: str,
                               total_to_withdraw: float) -> list[dict]:
        """Calculate suggested withdrawal distribution based on lot factors"""
        records = self.get_monthly_records(portfolio_id, month)
        if not records:
            return []

        # Calculate total weight (sum of lot factors)
        total_weight = sum(r["lot_factor"] for r in records)
        if total_weight == 0:
            return []

        # Calculate each account's share
        result = []
        for r in records:
            weight = r["lot_factor"] / total_weight
            suggested = total_to_withdraw * weight
            profit_pct = (r["profit"] / r["starting_balance"] * 100) if r["starting_balance"] > 0 else 0

            result.append({
                "account_id": r["account_id"],
                "account_name": r["account_name"],
                "lot_factor": r["lot_factor"],
                "starting_balance": r["starting_balance"],
                "ending_balance": r["ending_balance"],
                "profit": r["profit"],
                "profit_percent": round(profit_pct, 2),
                "weight": round(weight, 4),
                "suggested_withdrawal": round(suggested, 2),
                "actual_withdrawal": r["withdrawal"],
                "currency": r["currency"]
            })

        return result

    def close_elite_month(self, portfolio_id: int, month: str, elite_accounts: list[dict]) -> bool:
        """Close a month for Elite portfolio, saving remuneration/compound/transfer data"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    for acc in elite_accounts:
                        # Upsert the monthly record with Elite data
                        cur.execute("""
                            INSERT INTO portefeuille_monthly_records
                            (portfolio_id, account_id, month, lot_factor, starting_balance,
                             ending_balance, profit, withdrawal, remuneration, compound,
                             transfer_amount, level, is_closed, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, NOW())
                            ON CONFLICT (portfolio_id, account_id, month) DO UPDATE SET
                                ending_balance = EXCLUDED.ending_balance,
                                profit = EXCLUDED.profit,
                                remuneration = EXCLUDED.remuneration,
                                compound = EXCLUDED.compound,
                                transfer_amount = EXCLUDED.transfer_amount,
                                level = EXCLUDED.level,
                                is_closed = TRUE
                        """, (
                            portfolio_id,
                            acc["account_id"],
                            month,
                            acc["lot_factor"],
                            acc["starting_balance"],
                            acc["current_balance"],
                            acc["monthly_profit"],
                            acc.get("remuneration", 0),  # withdrawal = remuneration for Elite
                            acc.get("remuneration", 0),
                            acc.get("compound", 0),
                            acc.get("transfer", 0),
                            acc.get("level", "")
                        ))
                    return True
        except Exception as e:
            logger.error("Error closing Elite month", error=str(e))
            return False

    def get_elite_monthly_records(self, portfolio_id: int, month: str) -> list[dict]:
        """Get Elite monthly records with remuneration/compound/transfer data"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT pmr.id, pmr.account_id, pmr.month, pmr.lot_factor,
                               pmr.starting_balance, pmr.ending_balance, pmr.profit,
                               pmr.remuneration, pmr.compound, pmr.transfer_amount,
                               pmr.level, pmr.is_closed, ac.name, ac.currency
                        FROM portefeuille_monthly_records pmr
                        LEFT JOIN accounts_cache ac ON pmr.account_id = ac.id
                        WHERE pmr.portfolio_id = %s AND pmr.month = %s
                        ORDER BY pmr.lot_factor DESC
                    """, (portfolio_id, month))

                    return [
                        {
                            "id": row[0],
                            "account_id": row[1],
                            "month": row[2],
                            "lot_factor": row[3],
                            "starting_balance": row[4] or 0,
                            "ending_balance": row[5] or 0,
                            "profit": row[6] or 0,
                            "remuneration": row[7] or 0,
                            "compound": row[8] or 0,
                            "transfer": row[9] or 0,
                            "level": row[10] or "",
                            "is_closed": row[11] or False,
                            "account_name": row[12] or f"Account #{row[1]}",
                            "currency": row[13] or "EUR"
                        }
                        for row in cur.fetchall()
                    ]
        except Exception as e:
            logger.error("Error getting Elite monthly records", error=str(e))
            return []

    def is_month_closed(self, portfolio_id: int, month: str) -> bool:
        """Check if a month is already closed for a portfolio"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT is_closed FROM portefeuille_monthly_records
                        WHERE portfolio_id = %s AND month = %s AND is_closed = TRUE
                        LIMIT 1
                    """, (portfolio_id, month))
                    return cur.fetchone() is not None
        except Exception as e:
            logger.error("Error checking if month is closed", error=str(e))
            return False
