"""Monthly growth cache repository"""
import json
from datetime import datetime
from typing import Optional
from ..connection import get_connection
from config.logging import logger


class MonthlyGrowthCache:
    """Cache pour la croissance mensuelle globale"""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS monthly_growth_cache (
                        id SERIAL PRIMARY KEY,
                        data JSONB NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """)

    def save(self, data: list) -> bool:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM monthly_growth_cache")
                    cur.execute(
                        "INSERT INTO monthly_growth_cache (data, updated_at) VALUES (%s, %s)",
                        (json.dumps(data), datetime.now())
                    )
            return True
        except Exception as e:
            print(f"Erreur sauvegarde cache croissance mensuelle: {e}")
            return False

    def load(self) -> list | None:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT data FROM monthly_growth_cache LIMIT 1")
                    row = cur.fetchone()
                    if row:
                        return row[0]
        except Exception as e:
            print(f"Erreur chargement cache croissance mensuelle: {e}")
        return None

    def get_last_update(self) -> Optional[datetime]:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT updated_at FROM monthly_growth_cache LIMIT 1")
                    row = cur.fetchone()
                    if row:
                        return row[0]
        except Exception:
            pass
        return None

    def is_valid(self, max_age_hours: int = 24) -> bool:
        last_update = self.get_last_update()
        if not last_update:
            return False
        age = (datetime.now() - last_update).total_seconds() / 3600
        return age < max_age_hours
