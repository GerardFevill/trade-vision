"""MT5 Shared State - Mutable state shared across sub-services"""
from collections import deque
from models import HistoryPoint


class MT5SharedState:
    def __init__(self, history_max_size: int = 3600):
        self.history_max_size = history_max_size
        self.connected = False
        self.current_account_id = None
        self.current_terminal = None
        self.reset()

    def reset(self):
        """Reset account-specific data"""
        self.peak_balance = 0.0
        self.peak_equity = 0.0
        self.initial_deposit = 0.0
        self.history: deque[HistoryPoint] = deque(maxlen=self.history_max_size)
        self.max_drawdown = 0.0
        self.max_drawdown_percent = 0.0
