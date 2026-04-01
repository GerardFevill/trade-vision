"""Tests for MT5 TradeService"""
import pytest
from services.mt5.trade_service import TradeService
from tests.conftest import make_deal, make_position


class TestGetTradeStats:
    def test_no_deals_returns_empty_stats(self, mock_mt5, mt5_shared_state):
        mock_mt5.history_deals_get.return_value = None
        svc = TradeService(mt5_shared_state, mock_mt5)
        result = svc.get_trade_stats()
        assert result.total_trades == 0
        assert result.win_rate == 0

    def test_empty_deals_returns_empty_stats(self, mock_mt5, mt5_shared_state):
        mock_mt5.history_deals_get.return_value = []
        svc = TradeService(mt5_shared_state, mock_mt5)
        result = svc.get_trade_stats()
        assert result.total_trades == 0

    def test_winning_trades_stats(self, mock_mt5, mt5_shared_state):
        deals = [
            make_deal(ticket=1, type=0, entry=1, profit=100, commission=-1, swap=0),
            make_deal(ticket=2, type=1, entry=1, profit=200, commission=-2, swap=-1),
        ]
        mock_mt5.history_deals_get.return_value = deals
        mock_mt5.history_orders_get.return_value = None
        svc = TradeService(mt5_shared_state, mock_mt5)
        result = svc.get_trade_stats()
        assert result.total_trades == 2
        assert result.winning_trades == 2
        assert result.win_rate == pytest.approx(100.0)

    def test_mixed_trades_win_rate(self, mock_mt5, mt5_shared_state):
        deals = [
            make_deal(ticket=1, type=0, entry=1, profit=100, commission=0, swap=0),   # Win
            make_deal(ticket=2, type=1, entry=1, profit=-50, commission=0, swap=0),   # Loss
            make_deal(ticket=3, type=0, entry=1, profit=80, commission=0, swap=0),    # Win
            make_deal(ticket=4, type=1, entry=1, profit=-30, commission=0, swap=0),   # Loss
        ]
        mock_mt5.history_deals_get.return_value = deals
        mock_mt5.history_orders_get.return_value = None
        svc = TradeService(mt5_shared_state, mock_mt5)
        result = svc.get_trade_stats()
        assert result.total_trades == 4
        assert result.winning_trades == 2
        assert result.losing_trades == 2
        assert result.win_rate == pytest.approx(50.0)

    def test_profit_factor(self, mock_mt5, mt5_shared_state):
        deals = [
            make_deal(ticket=1, type=0, entry=1, profit=300, commission=0, swap=0),
            make_deal(ticket=2, type=1, entry=1, profit=-100, commission=0, swap=0),
        ]
        mock_mt5.history_deals_get.return_value = deals
        mock_mt5.history_orders_get.return_value = None
        svc = TradeService(mt5_shared_state, mock_mt5)
        result = svc.get_trade_stats()
        assert result.profit_factor == pytest.approx(3.0)

    def test_consecutive_wins_and_losses(self, mock_mt5, mt5_shared_state):
        deals = [
            make_deal(ticket=1, type=0, entry=1, profit=100, commission=0, swap=0),
            make_deal(ticket=2, type=0, entry=1, profit=100, commission=0, swap=0),
            make_deal(ticket=3, type=0, entry=1, profit=100, commission=0, swap=0),
            make_deal(ticket=4, type=1, entry=1, profit=-50, commission=0, swap=0),
            make_deal(ticket=5, type=1, entry=1, profit=-50, commission=0, swap=0),
        ]
        mock_mt5.history_deals_get.return_value = deals
        mock_mt5.history_orders_get.return_value = None
        svc = TradeService(mt5_shared_state, mock_mt5)
        result = svc.get_trade_stats()
        assert result.max_consecutive_wins == 3
        assert result.max_consecutive_losses == 2

    def test_best_and_worst_trade(self, mock_mt5, mt5_shared_state):
        deals = [
            make_deal(ticket=1, type=0, entry=1, profit=500, commission=-5, swap=0),   # Net 495
            make_deal(ticket=2, type=1, entry=1, profit=-200, commission=-3, swap=-2),  # Net -205
        ]
        mock_mt5.history_deals_get.return_value = deals
        mock_mt5.history_orders_get.return_value = None
        svc = TradeService(mt5_shared_state, mock_mt5)
        result = svc.get_trade_stats()
        assert result.best_trade == pytest.approx(495)
        assert result.worst_trade == pytest.approx(-205)

    def test_only_entry_in_deals_ignored(self, mock_mt5, mt5_shared_state):
        """Deals with entry=IN (opening) should not count as trades"""
        deals = [
            make_deal(ticket=1, type=0, entry=0, profit=0),  # Entry IN — not a closed trade
        ]
        mock_mt5.history_deals_get.return_value = deals
        mock_mt5.history_orders_get.return_value = None
        svc = TradeService(mt5_shared_state, mock_mt5)
        result = svc.get_trade_stats()
        assert result.total_trades == 0


class TestGetHistoryTrades:
    def test_empty_deals(self, mock_mt5, mt5_shared_state):
        mock_mt5.history_deals_get.return_value = None
        svc = TradeService(mt5_shared_state, mock_mt5)
        result = svc.get_history_trades(days=30)
        assert result == []

    def test_filters_only_buy_sell(self, mock_mt5, mt5_shared_state):
        deals = [
            make_deal(ticket=1, type=0),  # BUY
            make_deal(ticket=2, type=2),  # BALANCE — should be excluded
            make_deal(ticket=3, type=1),  # SELL
        ]
        mock_mt5.history_deals_get.return_value = deals
        svc = TradeService(mt5_shared_state, mock_mt5)
        result = svc.get_history_trades()
        assert len(result) == 2
        assert result[0].ticket == 1
        assert result[1].ticket == 3


class TestGetOpenPositions:
    def test_no_positions(self, mock_mt5, mt5_shared_state):
        mock_mt5.positions_get.return_value = None
        svc = TradeService(mt5_shared_state, mock_mt5)
        assert svc.get_open_positions() == []

    def test_position_mapping(self, mock_mt5, mt5_shared_state):
        pos = make_position(ticket=42, symbol="GBPUSD", type=1, profit=-30.0, sl=0, tp=0)
        mock_mt5.positions_get.return_value = [pos]
        svc = TradeService(mt5_shared_state, mock_mt5)
        result = svc.get_open_positions()
        assert len(result) == 1
        assert result[0].ticket == 42
        assert result[0].symbol == "GBPUSD"
        assert result[0].type == "SELL"
        assert result[0].profit == -30.0
        assert result[0].sl is None  # sl=0 → None
        assert result[0].tp is None  # tp=0 → None
