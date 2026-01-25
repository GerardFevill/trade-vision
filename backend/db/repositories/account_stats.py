"""Account stats repository - stores account statistics in DB"""
from datetime import datetime
from typing import Optional
from ..connection import get_connection


class AccountStatsRepository:
    """Stockage des statistiques de compte en base de données"""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Table pour les stats de compte
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS account_stats (
                        account_id INTEGER PRIMARY KEY,
                        balance REAL,
                        equity REAL,
                        profit REAL,
                        drawdown REAL,
                        drawdown_percent REAL,
                        initial_deposit REAL,
                        total_deposits REAL,
                        total_withdrawals REAL,
                        growth_percent REAL,
                        margin REAL,
                        free_margin REAL,
                        margin_level REAL,
                        leverage INTEGER,
                        currency TEXT,
                        server TEXT,
                        name TEXT,
                        last_deal_id INTEGER DEFAULT 0,
                        updated_at TIMESTAMP NOT NULL
                    )
                """)

                # Table pour les stats de trading
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS trade_stats (
                        account_id INTEGER PRIMARY KEY,
                        total_trades INTEGER,
                        winning_trades INTEGER,
                        losing_trades INTEGER,
                        win_rate REAL,
                        best_trade REAL,
                        worst_trade REAL,
                        gross_profit REAL,
                        gross_loss REAL,
                        profit_factor REAL,
                        average_profit REAL,
                        average_loss REAL,
                        max_consecutive_wins INTEGER,
                        max_consecutive_losses INTEGER,
                        longs_count INTEGER,
                        shorts_count INTEGER,
                        longs_won INTEGER,
                        shorts_won INTEGER,
                        avg_holding_time_seconds REAL,
                        expected_payoff REAL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """)

                # Table pour les métriques de risque
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS risk_metrics (
                        account_id INTEGER PRIMARY KEY,
                        max_drawdown REAL,
                        max_drawdown_percent REAL,
                        relative_drawdown_balance REAL,
                        relative_drawdown_equity REAL,
                        max_deposit_load REAL,
                        sharpe_ratio REAL,
                        recovery_factor REAL,
                        current_drawdown REAL,
                        current_drawdown_percent REAL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """)

                # Table pour l'historique des trades
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS trades_history (
                        id SERIAL PRIMARY KEY,
                        account_id INTEGER NOT NULL,
                        ticket BIGINT NOT NULL,
                        symbol TEXT,
                        type TEXT,
                        volume REAL,
                        open_time TIMESTAMP,
                        open_price REAL,
                        close_time TIMESTAMP,
                        close_price REAL,
                        profit REAL,
                        commission REAL,
                        swap REAL,
                        comment TEXT,
                        UNIQUE(account_id, ticket)
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_account ON trades_history(account_id, open_time DESC)")

    def save_account_stats(self, account_id: int, stats: dict) -> bool:
        """Sauvegarde les stats d'un compte"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO account_stats
                        (account_id, balance, equity, profit, drawdown, drawdown_percent,
                         initial_deposit, total_deposits, total_withdrawals, growth_percent,
                         margin, free_margin, margin_level, leverage, currency, server, name,
                         last_deal_id, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (account_id) DO UPDATE SET
                            balance = EXCLUDED.balance,
                            equity = EXCLUDED.equity,
                            profit = EXCLUDED.profit,
                            drawdown = EXCLUDED.drawdown,
                            drawdown_percent = EXCLUDED.drawdown_percent,
                            initial_deposit = EXCLUDED.initial_deposit,
                            total_deposits = EXCLUDED.total_deposits,
                            total_withdrawals = EXCLUDED.total_withdrawals,
                            growth_percent = EXCLUDED.growth_percent,
                            margin = EXCLUDED.margin,
                            free_margin = EXCLUDED.free_margin,
                            margin_level = EXCLUDED.margin_level,
                            leverage = EXCLUDED.leverage,
                            currency = EXCLUDED.currency,
                            server = EXCLUDED.server,
                            name = EXCLUDED.name,
                            last_deal_id = EXCLUDED.last_deal_id,
                            updated_at = EXCLUDED.updated_at
                    """, (
                        account_id,
                        stats.get('balance'), stats.get('equity'), stats.get('profit'),
                        stats.get('drawdown'), stats.get('drawdown_percent'),
                        stats.get('initial_deposit'), stats.get('total_deposits'),
                        stats.get('total_withdrawals'), stats.get('growth_percent'),
                        stats.get('margin'), stats.get('free_margin'), stats.get('margin_level'),
                        stats.get('leverage'), stats.get('currency'), stats.get('server'),
                        stats.get('name'), stats.get('last_deal_id', 0), datetime.now()
                    ))
            return True
        except Exception as e:
            print(f"Erreur sauvegarde account_stats: {e}")
            return False

    def get_account_stats(self, account_id: int) -> Optional[dict]:
        """Récupère les stats d'un compte"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT balance, equity, profit, drawdown, drawdown_percent,
                               initial_deposit, total_deposits, total_withdrawals, growth_percent,
                               margin, free_margin, margin_level, leverage, currency, server, name,
                               last_deal_id, updated_at
                        FROM account_stats WHERE account_id = %s
                    """, (account_id,))
                    row = cur.fetchone()
                    if row:
                        return {
                            'balance': row[0], 'equity': row[1], 'profit': row[2],
                            'drawdown': row[3], 'drawdown_percent': row[4],
                            'initial_deposit': row[5], 'total_deposits': row[6],
                            'total_withdrawals': row[7], 'growth_percent': row[8],
                            'margin': row[9], 'free_margin': row[10], 'margin_level': row[11],
                            'leverage': row[12], 'currency': row[13], 'server': row[14],
                            'name': row[15], 'last_deal_id': row[16], 'updated_at': row[17]
                        }
        except Exception as e:
            print(f"Erreur lecture account_stats: {e}")
        return None

    def get_last_deal_id(self, account_id: int) -> int:
        """Récupère le dernier deal_id connu pour un compte"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT last_deal_id FROM account_stats WHERE account_id = %s", (account_id,))
                    row = cur.fetchone()
                    return row[0] if row else 0
        except Exception:
            return 0

    def save_trade_stats(self, account_id: int, stats: dict) -> bool:
        """Sauvegarde les stats de trading"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO trade_stats
                        (account_id, total_trades, winning_trades, losing_trades, win_rate,
                         best_trade, worst_trade, gross_profit, gross_loss, profit_factor,
                         average_profit, average_loss, max_consecutive_wins, max_consecutive_losses,
                         longs_count, shorts_count, longs_won, shorts_won,
                         avg_holding_time_seconds, expected_payoff, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (account_id) DO UPDATE SET
                            total_trades = EXCLUDED.total_trades,
                            winning_trades = EXCLUDED.winning_trades,
                            losing_trades = EXCLUDED.losing_trades,
                            win_rate = EXCLUDED.win_rate,
                            best_trade = EXCLUDED.best_trade,
                            worst_trade = EXCLUDED.worst_trade,
                            gross_profit = EXCLUDED.gross_profit,
                            gross_loss = EXCLUDED.gross_loss,
                            profit_factor = EXCLUDED.profit_factor,
                            average_profit = EXCLUDED.average_profit,
                            average_loss = EXCLUDED.average_loss,
                            max_consecutive_wins = EXCLUDED.max_consecutive_wins,
                            max_consecutive_losses = EXCLUDED.max_consecutive_losses,
                            longs_count = EXCLUDED.longs_count,
                            shorts_count = EXCLUDED.shorts_count,
                            longs_won = EXCLUDED.longs_won,
                            shorts_won = EXCLUDED.shorts_won,
                            avg_holding_time_seconds = EXCLUDED.avg_holding_time_seconds,
                            expected_payoff = EXCLUDED.expected_payoff,
                            updated_at = EXCLUDED.updated_at
                    """, (
                        account_id,
                        stats.get('total_trades'), stats.get('winning_trades'),
                        stats.get('losing_trades'), stats.get('win_rate'),
                        stats.get('best_trade'), stats.get('worst_trade'),
                        stats.get('gross_profit'), stats.get('gross_loss'),
                        stats.get('profit_factor'), stats.get('average_profit'),
                        stats.get('average_loss'), stats.get('max_consecutive_wins'),
                        stats.get('max_consecutive_losses'), stats.get('longs_count'),
                        stats.get('shorts_count'), stats.get('longs_won'),
                        stats.get('shorts_won'), stats.get('avg_holding_time_seconds'),
                        stats.get('expected_payoff'), datetime.now()
                    ))
            return True
        except Exception as e:
            print(f"Erreur sauvegarde trade_stats: {e}")
            return False

    def get_trade_stats(self, account_id: int) -> Optional[dict]:
        """Récupère les stats de trading"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT total_trades, winning_trades, losing_trades, win_rate,
                               best_trade, worst_trade, gross_profit, gross_loss, profit_factor,
                               average_profit, average_loss, max_consecutive_wins, max_consecutive_losses,
                               longs_count, shorts_count, longs_won, shorts_won,
                               avg_holding_time_seconds, expected_payoff, updated_at
                        FROM trade_stats WHERE account_id = %s
                    """, (account_id,))
                    row = cur.fetchone()
                    if row:
                        return {
                            'total_trades': row[0], 'winning_trades': row[1],
                            'losing_trades': row[2], 'win_rate': row[3],
                            'best_trade': row[4], 'worst_trade': row[5],
                            'gross_profit': row[6], 'gross_loss': row[7],
                            'profit_factor': row[8], 'average_profit': row[9],
                            'average_loss': row[10], 'max_consecutive_wins': row[11],
                            'max_consecutive_losses': row[12], 'longs_count': row[13],
                            'shorts_count': row[14], 'longs_won': row[15],
                            'shorts_won': row[16], 'avg_holding_time_seconds': row[17],
                            'expected_payoff': row[18], 'updated_at': row[19]
                        }
        except Exception as e:
            print(f"Erreur lecture trade_stats: {e}")
        return None

    def save_risk_metrics(self, account_id: int, metrics: dict) -> bool:
        """Sauvegarde les métriques de risque"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO risk_metrics
                        (account_id, max_drawdown, max_drawdown_percent, relative_drawdown_balance,
                         relative_drawdown_equity, max_deposit_load, sharpe_ratio, recovery_factor,
                         current_drawdown, current_drawdown_percent, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (account_id) DO UPDATE SET
                            max_drawdown = EXCLUDED.max_drawdown,
                            max_drawdown_percent = EXCLUDED.max_drawdown_percent,
                            relative_drawdown_balance = EXCLUDED.relative_drawdown_balance,
                            relative_drawdown_equity = EXCLUDED.relative_drawdown_equity,
                            max_deposit_load = EXCLUDED.max_deposit_load,
                            sharpe_ratio = EXCLUDED.sharpe_ratio,
                            recovery_factor = EXCLUDED.recovery_factor,
                            current_drawdown = EXCLUDED.current_drawdown,
                            current_drawdown_percent = EXCLUDED.current_drawdown_percent,
                            updated_at = EXCLUDED.updated_at
                    """, (
                        account_id,
                        metrics.get('max_drawdown'), metrics.get('max_drawdown_percent'),
                        metrics.get('relative_drawdown_balance'), metrics.get('relative_drawdown_equity'),
                        metrics.get('max_deposit_load'), metrics.get('sharpe_ratio'),
                        metrics.get('recovery_factor'), metrics.get('current_drawdown'),
                        metrics.get('current_drawdown_percent'), datetime.now()
                    ))
            return True
        except Exception as e:
            print(f"Erreur sauvegarde risk_metrics: {e}")
            return False

    def get_risk_metrics(self, account_id: int) -> Optional[dict]:
        """Récupère les métriques de risque"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT max_drawdown, max_drawdown_percent, relative_drawdown_balance,
                               relative_drawdown_equity, max_deposit_load, sharpe_ratio,
                               recovery_factor, current_drawdown, current_drawdown_percent, updated_at
                        FROM risk_metrics WHERE account_id = %s
                    """, (account_id,))
                    row = cur.fetchone()
                    if row:
                        return {
                            'max_drawdown': row[0], 'max_drawdown_percent': row[1],
                            'relative_drawdown_balance': row[2], 'relative_drawdown_equity': row[3],
                            'max_deposit_load': row[4], 'sharpe_ratio': row[5],
                            'recovery_factor': row[6], 'current_drawdown': row[7],
                            'current_drawdown_percent': row[8], 'updated_at': row[9]
                        }
        except Exception as e:
            print(f"Erreur lecture risk_metrics: {e}")
        return None

    def save_trades(self, account_id: int, trades: list) -> bool:
        """Sauvegarde l'historique des trades"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    for t in trades:
                        cur.execute("""
                            INSERT INTO trades_history
                            (account_id, ticket, symbol, type, volume, open_time, open_price,
                             close_time, close_price, profit, commission, swap, comment)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (account_id, ticket) DO NOTHING
                        """, (
                            account_id, t.get('ticket'), t.get('symbol'), t.get('type'),
                            t.get('volume'), t.get('open_time'), t.get('open_price'),
                            t.get('close_time'), t.get('close_price'), t.get('profit'),
                            t.get('commission'), t.get('swap'), t.get('comment')
                        ))
            return True
        except Exception as e:
            print(f"Erreur sauvegarde trades: {e}")
            return False

    def get_trades(self, account_id: int, limit: int = 100) -> list:
        """Récupère l'historique des trades"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT ticket, symbol, type, volume, open_time, open_price,
                               close_time, close_price, profit, commission, swap, comment
                        FROM trades_history
                        WHERE account_id = %s
                        ORDER BY open_time DESC
                        LIMIT %s
                    """, (account_id, limit))
                    return [
                        {
                            'ticket': row[0], 'symbol': row[1], 'type': row[2],
                            'volume': row[3], 'open_time': row[4], 'open_price': row[5],
                            'close_time': row[6], 'close_price': row[7], 'profit': row[8],
                            'commission': row[9], 'swap': row[10], 'comment': row[11]
                        }
                        for row in cur.fetchall()
                    ]
        except Exception as e:
            print(f"Erreur lecture trades: {e}")
            return []


# Instance globale
account_stats_repo = AccountStatsRepository()
