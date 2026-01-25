"""Database module"""
from .connection import get_connection, DB_CONFIG
from .repositories.history import HistoryDatabase
from .repositories.accounts_cache import AccountsCache
from .repositories.balance_history import AccountBalanceHistory
from .repositories.growth_cache import MonthlyGrowthCache
from .repositories.account_stats import AccountStatsRepository, account_stats_repo

# Global instances
history_db = HistoryDatabase()
accounts_cache = AccountsCache()
account_balance_history = AccountBalanceHistory()
monthly_growth_cache = MonthlyGrowthCache()

__all__ = [
    'get_connection', 'DB_CONFIG',
    'HistoryDatabase', 'AccountsCache', 'AccountBalanceHistory', 'MonthlyGrowthCache',
    'AccountStatsRepository', 'account_stats_repo',
    'history_db', 'accounts_cache', 'account_balance_history', 'monthly_growth_cache'
]
