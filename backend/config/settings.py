"""Application settings using pydantic-settings"""
import json
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MT5Account(BaseSettings):
    """MT5 Account configuration"""
    id: int
    password: str
    server: str
    name: str
    terminal: str


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="mt5monitor")
    postgres_user: str = Field(default="mt5user")
    postgres_password: str = Field(default="mt5password")
    postgres_pool_min: int = Field(default=2)
    postgres_pool_max: int = Field(default=10)

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    cors_origins: List[str] = Field(default=["http://localhost:4200"])

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")  # json or console
    log_file: Optional[str] = Field(default=None)

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=100)

    # MT5 Terminals
    mt5_terminal_roboforex: Optional[str] = Field(default=None)
    mt5_terminal_icmarkets: Optional[str] = Field(default=None)

    # MT5 Accounts (JSON string)
    mt5_accounts: str = Field(default="[]")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from JSON string or list"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Assume comma-separated
                return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def db_config(self) -> dict:
        """Get database configuration dict"""
        return {
            "host": self.postgres_host,
            "port": self.postgres_port,
            "dbname": self.postgres_db,
            "user": self.postgres_user,
            "password": self.postgres_password,
        }

    @property
    def mt5_terminals(self) -> dict:
        """Get MT5 terminals configuration"""
        terminals = {}
        if self.mt5_terminal_roboforex:
            terminals["roboforex"] = self.mt5_terminal_roboforex
        if self.mt5_terminal_icmarkets:
            terminals["icmarkets"] = self.mt5_terminal_icmarkets
        return terminals

    def get_mt5_accounts(self) -> List[dict]:
        """Parse and return MT5 accounts from JSON string"""
        try:
            accounts = json.loads(self.mt5_accounts)
            return accounts if isinstance(accounts, list) else []
        except json.JSONDecodeError:
            return []


# Global settings instance
settings = Settings()
