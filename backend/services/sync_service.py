"""Sync Service - Synchronise les données MT5 vers la base de données avec détection de changements"""
import os
from datetime import datetime, timedelta

MT5_MODE = os.environ.get('MT5_MODE', 'direct')

if MT5_MODE == 'bridge':
    from .mt5_bridge_client import mt5_bridge as mt5
else:
    try:
        import MetaTrader5 as mt5
    except ImportError:
        from . import mt5_mock as mt5
from typing import Optional
from config import MT5_ACCOUNTS, MT5_TERMINALS
from db import account_stats_repo, accounts_cache, account_balance_history
from models import AccountSummary
from config.logging import logger


class SyncService:
    """Service de synchronisation MT5 -> DB avec détection de changements"""

    def __init__(self):
        self.last_sync = {}  # account_id -> datetime

    def get_latest_deal_id(self) -> int:
        """Récupère l'ID du dernier deal depuis MT5"""
        deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
        if deals and len(deals) > 0:
            return max(d.ticket for d in deals)
        return 0

    def has_changes(self, account_id: int) -> bool:
        """Vérifie si le compte a de nouveaux deals"""
        stored_deal_id = account_stats_repo.get_last_deal_id(account_id)
        current_deal_id = self.get_latest_deal_id()
        return current_deal_id > stored_deal_id

    def sync_account(self, account_id: int, force: bool = False) -> bool:
        """Synchronise un compte si nécessaire

        Args:
            account_id: ID du compte MT5
            force: Forcer la sync même si pas de changement

        Returns:
            True si sync effectuée, False sinon
        """
        # Vérifier si changement nécessaire
        if not force and not self.has_changes(account_id):
            logger.debug("Account has no changes", account_id=account_id)
            return False

        logger.info("Syncing account", account_id=account_id)

        # Récupérer les infos du compte
        info = mt5.account_info()
        if not info:
            logger.error("Cannot retrieve account info", account_id=account_id)
            return False

        # Récupérer les deals
        deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
        latest_deal_id = max(d.ticket for d in deals) if deals else 0

        # Calculer les stats
        total_deposits = 0.0
        total_withdrawals = 0.0
        trades_list = []
        winning_trades = 0
        losing_trades = 0
        profits = []
        longs = []
        shorts = []

        if deals:
            for d in deals:
                if d.type == mt5.DEAL_TYPE_BALANCE:
                    if d.profit > 0:
                        total_deposits += d.profit
                    else:
                        total_withdrawals += abs(d.profit)
                elif d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
                    if d.entry == mt5.DEAL_ENTRY_OUT:
                        profit = d.profit + d.commission + d.swap
                        profits.append(profit)
                        if profit > 0:
                            winning_trades += 1
                        else:
                            losing_trades += 1

                        if d.type == mt5.DEAL_TYPE_SELL:
                            longs.append(d)
                        else:
                            shorts.append(d)

                        trades_list.append({
                            'ticket': d.ticket,
                            'symbol': d.symbol,
                            'type': 'BUY' if d.type == mt5.DEAL_TYPE_BUY else 'SELL',
                            'volume': d.volume,
                            'open_time': datetime.fromtimestamp(d.time),
                            'open_price': d.price,
                            'close_time': None,
                            'close_price': None,
                            'profit': d.profit,
                            'commission': d.commission,
                            'swap': d.swap,
                            'comment': d.comment or ''
                        })

        # Calculer les métriques
        net_deposit = total_deposits - total_withdrawals
        total_profit = info.balance - net_deposit if net_deposit > 0 else info.profit
        total_trades = len(profits)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        gross_profit = sum(p for p in profits if p > 0)
        gross_loss = abs(sum(p for p in profits if p < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

        # Sauvegarder les stats du compte
        account_stats = {
            'balance': info.balance,
            'equity': info.equity,
            'profit': total_profit,
            'drawdown': 0,  # Calculé séparément
            'drawdown_percent': 0,
            'initial_deposit': total_deposits,
            'total_deposits': total_deposits,
            'total_withdrawals': total_withdrawals,
            'growth_percent': (total_profit / net_deposit * 100) if net_deposit > 0 else 0,
            'margin': info.margin,
            'free_margin': info.margin_free,
            'margin_level': info.margin_level,
            'leverage': info.leverage,
            'currency': info.currency,
            'server': info.server,
            'name': info.name,
            'last_deal_id': latest_deal_id
        }
        account_stats_repo.save_account_stats(account_id, account_stats)

        # Sauvegarder les stats de trading
        longs_won = len([t for t in longs if (t.profit + t.commission + t.swap) > 0])
        shorts_won = len([t for t in shorts if (t.profit + t.commission + t.swap) > 0])

        trade_stats = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'best_trade': max(profits) if profits else 0,
            'worst_trade': min(profits) if profits else 0,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'profit_factor': profit_factor,
            'average_profit': (gross_profit / winning_trades) if winning_trades > 0 else 0,
            'average_loss': (gross_loss / losing_trades) if losing_trades > 0 else 0,
            'max_consecutive_wins': self._calc_consecutive_wins(profits),
            'max_consecutive_losses': self._calc_consecutive_losses(profits),
            'longs_count': len(longs),
            'shorts_count': len(shorts),
            'longs_won': longs_won,
            'shorts_won': shorts_won,
            'avg_holding_time_seconds': 0,
            'expected_payoff': (sum(profits) / len(profits)) if profits else 0
        }
        account_stats_repo.save_trade_stats(account_id, trade_stats)

        # Calculer les métriques de risque depuis l'historique des deals
        max_drawdown, max_drawdown_pct, peak_balance = self._calc_max_drawdown(deals)
        current_dd = max(0, peak_balance - info.balance) if peak_balance > 0 else 0
        current_dd_pct = (current_dd / peak_balance * 100) if peak_balance > 0 else 0

        # Sharpe ratio simplifié (basé sur les profits des trades)
        sharpe_ratio = self._calc_sharpe_ratio(profits)

        # Recovery factor = profit net / max drawdown
        recovery_factor = (total_profit / max_drawdown) if max_drawdown > 0 else 0

        risk_metrics = {
            'max_drawdown': max_drawdown,
            'max_drawdown_percent': max_drawdown_pct,
            'relative_drawdown_balance': max_drawdown_pct,
            'relative_drawdown_equity': current_dd_pct,
            'max_deposit_load': (info.margin / info.equity * 100) if info.equity > 0 else 0,
            'sharpe_ratio': round(sharpe_ratio, 2),
            'recovery_factor': round(recovery_factor, 2),
            'current_drawdown': current_dd,
            'current_drawdown_percent': current_dd_pct
        }
        account_stats_repo.save_risk_metrics(account_id, risk_metrics)

        # Sauvegarder les trades récents
        account_stats_repo.save_trades(account_id, trades_list[-100:])

        self.last_sync[account_id] = datetime.now()
        logger.info("Account sync completed", account_id=account_id, total_trades=total_trades)
        return True

    def _calc_consecutive_wins(self, profits: list) -> int:
        max_wins = current = 0
        for p in profits:
            if p > 0:
                current += 1
                max_wins = max(max_wins, current)
            else:
                current = 0
        return max_wins

    def _calc_consecutive_losses(self, profits: list) -> int:
        max_losses = current = 0
        for p in profits:
            if p < 0:
                current += 1
                max_losses = max(max_losses, current)
            else:
                current = 0
        return max_losses

    def _calc_max_drawdown(self, deals) -> tuple:
        """Calcule le drawdown maximum depuis l'historique des deals.

        Drawdown = (pic_équité - creux_équité) / pic_équité * 100
        On reconstruit l'historique de la balance et on calcule le drawdown max.

        Returns:
            tuple: (max_drawdown_value, max_drawdown_percent, current_peak)
        """
        if not deals:
            return 0, 0, 0

        # Reconstituer l'historique de la balance chronologiquement
        balance = 0.0
        peak_balance = 0.0
        max_drawdown = 0.0
        max_drawdown_pct = 0.0

        sorted_deals = sorted(deals, key=lambda x: x.time)

        for d in sorted_deals:
            if d.type == mt5.DEAL_TYPE_BALANCE:
                # Dépôt ou retrait
                balance += d.profit
            elif d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
                # Trade fermé
                balance += d.profit + d.commission + d.swap

            # Mettre à jour le pic si nouveau maximum
            if balance > peak_balance:
                peak_balance = balance

            # Calculer le drawdown courant (uniquement si on a un pic positif)
            if peak_balance > 0 and balance < peak_balance:
                current_dd = peak_balance - balance
                current_dd_pct = (current_dd / peak_balance) * 100

                # Garder le max drawdown
                if current_dd > max_drawdown:
                    max_drawdown = current_dd
                if current_dd_pct > max_drawdown_pct:
                    max_drawdown_pct = current_dd_pct

        # Limiter le % à 100 max (ne peut pas perdre plus que 100%)
        max_drawdown_pct = min(max_drawdown_pct, 100.0)

        return round(max_drawdown, 2), round(max_drawdown_pct, 2), round(peak_balance, 2)

    def _calc_sharpe_ratio(self, profits: list) -> float:
        """Calcule le ratio de Sharpe simplifié basé sur les profits des trades.

        Sharpe = moyenne des returns / écart-type des returns
        """
        if len(profits) < 10:
            return 0.0

        avg_profit = sum(profits) / len(profits)
        variance = sum((p - avg_profit) ** 2 for p in profits) / len(profits)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return 0.0

        # Sharpe simplifié (sans taux sans risque)
        return avg_profit / std_dev

    def sync_all_accounts(self, force: bool = False) -> dict:
        """Synchronise tous les comptes configurés

        Returns:
            dict avec le résultat par compte
        """
        results = {}

        for acc_config in MT5_ACCOUNTS:
            account_id = acc_config["id"]
            terminal_key = acc_config.get("terminal", "roboforex")
            terminal_path = MT5_TERMINALS.get(terminal_key)

            try:
                # Se connecter au compte
                mt5.shutdown()
                init_params = {
                    "login": acc_config["id"],
                    "password": acc_config["password"],
                    "server": acc_config["server"],
                    "timeout": 60000
                }
                if terminal_path:
                    init_params["path"] = terminal_path

                if not mt5.initialize(**init_params):
                    results[account_id] = {"status": "error", "message": str(mt5.last_error())}
                    continue

                # Synchroniser
                synced = self.sync_account(account_id, force)
                results[account_id] = {
                    "status": "synced" if synced else "no_change",
                    "last_sync": self.last_sync.get(account_id)
                }

            except Exception as e:
                results[account_id] = {"status": "error", "message": str(e)}

        return results

    def quick_check_all(self) -> dict:
        """Vérifie rapidement quels comptes ont des changements (sans sync)"""
        changes = {}

        for acc_config in MT5_ACCOUNTS:
            account_id = acc_config["id"]
            stored_deal_id = account_stats_repo.get_last_deal_id(account_id)
            changes[account_id] = {
                "stored_deal_id": stored_deal_id,
                "needs_check": stored_deal_id == 0  # Jamais sync
            }

        return changes


# Instance globale
sync_service = SyncService()
