"""
Script de migration SQLite vers PostgreSQL
"""
import sqlite3
import psycopg2
from datetime import datetime
import json

# Configuration
SQLITE_PATH = "mt5_history.db"
PG_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'database': 'mt5monitor',
    'user': 'mt5user',
    'password': 'mt5password',
}


def migrate():
    print("=== Migration SQLite -> PostgreSQL ===\n")

    # Connexion SQLite
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_cur = sqlite_conn.cursor()

    # Connexion PostgreSQL
    pg_conn = psycopg2.connect(**PG_CONFIG)
    pg_cur = pg_conn.cursor()

    # Créer les tables PostgreSQL
    print("Création des tables PostgreSQL...")

    pg_cur.execute("""
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

    pg_cur.execute("""
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
            updated_at TIMESTAMP NOT NULL
        )
    """)

    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS account_balance_history (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            balance REAL NOT NULL,
            equity REAL NOT NULL,
            UNIQUE(account_id, timestamp)
        )
    """)

    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS monthly_growth_cache (
            id SERIAL PRIMARY KEY,
            data JSONB NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
    """)

    pg_conn.commit()

    # Migrer history_v2 -> history
    print("\nMigration de l'historique...")
    try:
        sqlite_cur.execute("SELECT account_id, timestamp, balance, equity, drawdown, drawdown_percent FROM history_v2")
        rows = sqlite_cur.fetchall()
        count = 0
        for row in rows:
            try:
                ts = datetime.fromisoformat(row[1]) if isinstance(row[1], str) else row[1]
                pg_cur.execute("""
                    INSERT INTO history (account_id, timestamp, balance, equity, drawdown, drawdown_percent)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (account_id, timestamp) DO NOTHING
                """, (row[0], ts, row[2], row[3], row[4], row[5]))
                count += 1
            except Exception as e:
                print(f"  Erreur ligne: {e}")
        pg_conn.commit()
        print(f"  -> {count} points d'historique migrés")
    except Exception as e:
        print(f"  Erreur: {e}")

    # Migrer accounts_cache
    print("\nMigration du cache des comptes...")
    try:
        sqlite_cur.execute("""
            SELECT id, name, broker, server, balance, equity, profit, profit_percent,
                   drawdown, trades, win_rate, currency, leverage, connected, updated_at
            FROM accounts_cache
        """)
        rows = sqlite_cur.fetchall()
        count = 0
        for row in rows:
            try:
                ts = datetime.fromisoformat(row[14]) if isinstance(row[14], str) else row[14]
                connected = bool(row[13]) if row[13] is not None else False
                pg_cur.execute("""
                    INSERT INTO accounts_cache
                    (id, name, broker, server, balance, equity, profit, profit_percent,
                     drawdown, trades, win_rate, currency, leverage, connected, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        balance = EXCLUDED.balance,
                        updated_at = EXCLUDED.updated_at
                """, (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7],
                      row[8], row[9], row[10], row[11], row[12], connected, ts))
                count += 1
            except Exception as e:
                print(f"  Erreur ligne {row[0]}: {e}")
        pg_conn.commit()
        print(f"  -> {count} comptes migrés")
    except Exception as e:
        print(f"  Erreur: {e}")

    # Migrer account_balance_history
    print("\nMigration des sparklines...")
    try:
        sqlite_cur.execute("SELECT account_id, timestamp, balance, equity FROM account_balance_history")
        rows = sqlite_cur.fetchall()
        count = 0
        for row in rows:
            try:
                ts = datetime.fromisoformat(row[1]) if isinstance(row[1], str) else row[1]
                pg_cur.execute("""
                    INSERT INTO account_balance_history (account_id, timestamp, balance, equity)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (account_id, timestamp) DO NOTHING
                """, (row[0], ts, row[2], row[3]))
                count += 1
            except Exception as e:
                print(f"  Erreur: {e}")
        pg_conn.commit()
        print(f"  -> {count} snapshots migrés")
    except Exception as e:
        print(f"  Erreur: {e}")

    # Migrer monthly_growth_cache
    print("\nMigration du cache croissance mensuelle...")
    try:
        sqlite_cur.execute("SELECT data, updated_at FROM monthly_growth_cache LIMIT 1")
        row = sqlite_cur.fetchone()
        if row:
            data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            ts = datetime.fromisoformat(row[1]) if isinstance(row[1], str) else row[1]
            pg_cur.execute("DELETE FROM monthly_growth_cache")
            pg_cur.execute("""
                INSERT INTO monthly_growth_cache (data, updated_at)
                VALUES (%s, %s)
            """, (json.dumps(data), ts))
            pg_conn.commit()
            print("  -> Cache migré")
        else:
            print("  -> Pas de cache à migrer")
    except Exception as e:
        print(f"  Erreur: {e}")

    # Créer les index
    print("\nCréation des index...")
    pg_cur.execute("CREATE INDEX IF NOT EXISTS idx_history_account_timestamp ON history(account_id, timestamp)")
    pg_cur.execute("CREATE INDEX IF NOT EXISTS idx_balance_history_account ON account_balance_history(account_id, timestamp)")
    pg_conn.commit()

    # Stats finales
    print("\n=== Vérification ===")
    pg_cur.execute("SELECT COUNT(*) FROM history")
    print(f"history: {pg_cur.fetchone()[0]} lignes")
    pg_cur.execute("SELECT COUNT(*) FROM accounts_cache")
    print(f"accounts_cache: {pg_cur.fetchone()[0]} lignes")
    pg_cur.execute("SELECT COUNT(*) FROM account_balance_history")
    print(f"account_balance_history: {pg_cur.fetchone()[0]} lignes")
    pg_cur.execute("SELECT COUNT(*) FROM monthly_growth_cache")
    print(f"monthly_growth_cache: {pg_cur.fetchone()[0]} lignes")

    # Fermer les connexions
    sqlite_conn.close()
    pg_conn.close()

    print("\n=== Migration terminée! ===")


if __name__ == "__main__":
    migrate()
