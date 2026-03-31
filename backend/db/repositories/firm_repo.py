"""Firm & Profile repository"""
from datetime import datetime
from typing import Optional
from ..connection import get_connection
from models import Firm, Profile, FirmWithProfiles
from config.logging import logger


class FirmRepository:
    """Repository for firm and profile management"""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS firms (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS profiles (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        firm_id INTEGER REFERENCES firms(id) ON DELETE CASCADE,
                        is_default BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)

                # Case-insensitive uniqueness
                cur.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_firms_name_lower
                    ON firms (LOWER(name))
                """)
                cur.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_profiles_name_lower
                    ON profiles (LOWER(name))
                """)

                # Seed firms (idempotent)
                cur.execute("""
                    INSERT INTO firms (name) VALUES ('NOUGLOZEH')
                    ON CONFLICT (name) DO NOTHING
                """)
                cur.execute("""
                    INSERT INTO firms (name) VALUES ('CosmosElite')
                    ON CONFLICT (name) DO NOTHING
                """)

                cur.execute("SELECT id FROM firms WHERE name = 'NOUGLOZEH'")
                nouglozeh_id = cur.fetchone()[0]

                cur.execute("SELECT id FROM firms WHERE name = 'CosmosElite'")
                cosmos_id = cur.fetchone()[0]

                # Seed profiles
                for name, firm_id, is_default in [
                    ('Fevill', nouglozeh_id, True),
                    ('Akaj', nouglozeh_id, False),
                    ('Vitogbe', nouglozeh_id, False),
                    ('CosmosElite', cosmos_id, True),
                ]:
                    cur.execute("""
                        INSERT INTO profiles (name, firm_id, is_default)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (name) DO NOTHING
                    """, (name, firm_id, is_default))

    # --- Firms ---

    def list_firms(self) -> list[Firm]:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, name, created_at, updated_at
                        FROM firms ORDER BY id
                    """)
                    return [
                        Firm(id=r[0], name=r[1], created_at=r[2], updated_at=r[3])
                        for r in cur.fetchall()
                    ]
        except Exception as e:
            logger.error("Error listing firms", error=str(e))
            return []

    def get_firm_with_profiles(self, firm_id: int) -> Optional[FirmWithProfiles]:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, name, created_at, updated_at
                        FROM firms WHERE id = %s
                    """, (firm_id,))
                    row = cur.fetchone()
                    if not row:
                        return None

                    firm = FirmWithProfiles(
                        id=row[0], name=row[1],
                        created_at=row[2], updated_at=row[3],
                        profiles=[]
                    )

                    cur.execute("""
                        SELECT id, name, firm_id, is_default, created_at, updated_at
                        FROM profiles WHERE firm_id = %s ORDER BY is_default DESC, name
                    """, (firm_id,))
                    firm.profiles = [
                        Profile(
                            id=r[0], name=r[1], firm_id=r[2],
                            is_default=r[3], created_at=r[4], updated_at=r[5]
                        )
                        for r in cur.fetchall()
                    ]
                    return firm
        except Exception as e:
            logger.error("Error getting firm with profiles", error=str(e))
            return None

    def create_firm(self, name: str) -> Optional[Firm]:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    now = datetime.now()
                    cur.execute("""
                        INSERT INTO firms (name, created_at, updated_at)
                        VALUES (%s, %s, %s) RETURNING id
                    """, (name, now, now))
                    fid = cur.fetchone()[0]
                    return Firm(id=fid, name=name, created_at=now, updated_at=now)
        except Exception as e:
            logger.error("Error creating firm", error=str(e))
            return None

    def delete_firm(self, firm_id: int) -> bool:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM firms WHERE id = %s", (firm_id,))
                    return cur.rowcount > 0
        except Exception as e:
            logger.error("Error deleting firm", error=str(e))
            return False

    # --- Profiles ---

    def list_profiles(self, firm_id: Optional[int] = None) -> list[Profile]:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    if firm_id:
                        cur.execute("""
                            SELECT id, name, firm_id, is_default, created_at, updated_at
                            FROM profiles WHERE firm_id = %s ORDER BY is_default DESC, name
                        """, (firm_id,))
                    else:
                        cur.execute("""
                            SELECT id, name, firm_id, is_default, created_at, updated_at
                            FROM profiles ORDER BY firm_id, is_default DESC, name
                        """)
                    return [
                        Profile(
                            id=r[0], name=r[1], firm_id=r[2],
                            is_default=r[3], created_at=r[4], updated_at=r[5]
                        )
                        for r in cur.fetchall()
                    ]
        except Exception as e:
            logger.error("Error listing profiles", error=str(e))
            return []

    def list_profile_names(self) -> list[str]:
        """Return just the profile names (for client dropdowns)"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT name FROM profiles
                        WHERE is_default = FALSE
                        ORDER BY firm_id, name
                    """)
                    return [r[0] for r in cur.fetchall()]
        except Exception as e:
            logger.error("Error listing profile names", error=str(e))
            return []

    def create_profile(self, name: str, firm_id: int, is_default: bool = False) -> Optional[Profile]:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    now = datetime.now()
                    cur.execute("""
                        INSERT INTO profiles (name, firm_id, is_default, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id
                    """, (name, firm_id, is_default, now, now))
                    pid = cur.fetchone()[0]
                    return Profile(
                        id=pid, name=name, firm_id=firm_id,
                        is_default=is_default, created_at=now, updated_at=now
                    )
        except Exception as e:
            logger.error("Error creating profile", error=str(e))
            return None

    def delete_profile(self, profile_id: int) -> bool:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM profiles WHERE id = %s", (profile_id,))
                    return cur.rowcount > 0
        except Exception as e:
            logger.error("Error deleting profile", error=str(e))
            return False
