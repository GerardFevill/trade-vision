"""MT5 Connector Service - Core trading platform integration"""
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from collections import deque
from models import (
    AccountInfo, AccountStats, TradeStats, RiskMetrics,
    Trade, Position, HistoryPoint, ConnectionStatus, FullDashboard, MonthlyGrowth,
    DailyDrawdown, AccountSummary
)
from db import history_db, accounts_cache, account_balance_history, monthly_growth_cache
from config import MT5_ACCOUNTS, MT5_TERMINALS
from config.logging import logger


class MT5Connector:
    def __init__(self, history_max_size: int = 3600):
        self.connected = False
        self.current_account_id = None
        self.current_terminal = None
        self.history_max_size = history_max_size
        self._reset_account_data()

    def _reset_account_data(self):
        """Réinitialise les données spécifiques au compte"""
        self.peak_balance = 0.0
        self.peak_equity = 0.0
        self.initial_deposit = 0.0
        self.history: deque[HistoryPoint] = deque(maxlen=self.history_max_size)
        self.max_drawdown = 0.0
        self.max_drawdown_percent = 0.0

    def _load_history_from_db(self, account_id: int):
        """Charge l'historique depuis la base de données pour un compte spécifique"""
        db_history = history_db.load_history(account_id, days=730)  # Charger 2 ans d'historique
        self.history.clear()
        for point in db_history:
            self.history.append(point)
        if db_history:
            # Utiliser les valeurs du dernier point comme référence (pas le max historique)
            last_point = db_history[-1]
            self.peak_balance = last_point.balance
            self.peak_equity = last_point.equity
            # Ne pas restaurer max_drawdown - le recalculer depuis les données actuelles
            self.max_drawdown = 0.0
            self.max_drawdown_percent = 0.0
            logger.info("History loaded for account", account_id=account_id, points=len(db_history))
        else:
            # Pas d'historique - commencer frais avec les valeurs actuelles
            logger.info("No history for account, starting fresh", account_id=account_id)
            info = mt5.account_info()
            if info:
                self.peak_balance = info.balance
                self.peak_equity = info.equity

    def connect(self, account_id: int = None, retries: int = 2, timeout: int = 60000) -> bool:
        """Connecte à MT5, optionnellement à un compte spécifique

        Args:
            account_id: ID du compte MT5
            retries: Nombre de tentatives en cas d'échec
            timeout: Timeout de connexion en millisecondes (défaut: 60s)
        """
        import time

        # Vérifier si on change de compte
        switching_account = account_id and account_id != self.current_account_id

        # Si pas d'account_id spécifié, utiliser le premier compte de la config
        if not account_id:
            if MT5_ACCOUNTS:
                account_id = MT5_ACCOUNTS[0]["id"]
            else:
                logger.warning("No accounts configured")
                return False

        # Trouver le compte dans la config
        account_config = None
        for acc in MT5_ACCOUNTS:
            if acc["id"] == account_id:
                account_config = acc
                break

        if not account_config:
            logger.error("Account not found in config", account_id=account_id)
            return False

        terminal_key = account_config.get("terminal", "roboforex")
        terminal_path = MT5_TERMINALS.get(terminal_key)

        # Tentatives de connexion avec retry
        for attempt in range(retries + 1):
            # Fermer toute connexion existante
            mt5.shutdown()

            # Initialiser MT5 avec les identifiants (connexion directe)
            init_params = {
                "login": account_config["id"],
                "password": account_config["password"],
                "server": account_config["server"],
                "timeout": timeout
            }

            # Ajouter le chemin du terminal si disponible
            if terminal_path:
                init_params["path"] = terminal_path

            if mt5.initialize(**init_params):
                # Connexion réussie
                logger.info("MT5 connected to account", account_id=account_id, server=account_config['server'])
                break
            else:
                error = mt5.last_error()
                logger.warning("MT5 connection failed", account_id=account_id, attempt=attempt + 1, max_attempts=retries + 1, error=str(error))
                if attempt < retries:
                    time.sleep(2)
                    continue
                return False

        self.current_account_id = account_id
        self.current_terminal = terminal_key

        # Réinitialiser et charger les données spécifiques au compte
        if switching_account:
            self._reset_account_data()
            self._load_history_from_db(account_id)

        self.connected = True
        info = mt5.account_info()
        if info:
            # Si c'est un nouveau compte ou pas d'account_id précédent
            if self.current_account_id != info.login:
                self.current_account_id = info.login
                self._reset_account_data()
                self._load_history_from_db(info.login)

            # Mettre à jour les peaks avec les valeurs actuelles si plus hautes
            self.peak_balance = max(self.peak_balance, info.balance)
            self.peak_equity = max(self.peak_equity, info.equity)
            if self.initial_deposit == 0:
                self._calculate_initial_deposit()
        return True

    def disconnect(self):
        mt5.shutdown()
        self.connected = False

    def _calculate_initial_deposit(self):
        deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
        if deals:
            deposits = [d.profit for d in deals if d.type == mt5.DEAL_TYPE_BALANCE and d.profit > 0]
            self.initial_deposit = deposits[0] if deposits else 0

    def get_connection_status(self) -> ConnectionStatus:
        if not self.connected:
            return ConnectionStatus(connected=False, server=None, account=None, name=None, company=None)
        info = mt5.account_info()
        if not info:
            return ConnectionStatus(connected=False, server=None, account=None, name=None, company=None)
        return ConnectionStatus(
            connected=True,
            server=info.server,
            account=info.login,
            name=info.name,
            company=info.company
        )

    def get_account_info(self) -> AccountInfo | None:
        if not self.connected and not self.connect():
            return None
        info = mt5.account_info()
        if not info:
            return None

        trade_modes = {0: "Demo", 1: "Contest", 2: "Real"}

        return AccountInfo(
            balance=info.balance,
            equity=info.equity,
            margin=info.margin,
            free_margin=info.margin_free,
            margin_level=info.margin_level if info.margin_level else None,
            profit=info.profit,
            leverage=info.leverage,
            server=info.server,
            name=info.name,
            login=info.login,
            currency=info.currency,
            trade_mode=trade_modes.get(info.trade_mode, "Unknown")
        )

    def _calculate_monthly_growth(self, deals, current_balance: float) -> float:
        """Calcule la croissance depuis le début du mois en cours"""
        if not deals:
            return 0.0

        # Trouver le 1er jour du mois en cours
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1)
        start_timestamp = start_of_month.timestamp()

        # Calculer la balance au début du mois
        # = somme de tous les deals (balance + trades) avant le 1er du mois
        balance_start_of_month = 0.0
        for d in sorted(deals, key=lambda x: x.time):
            if d.time < start_timestamp:
                if d.type == mt5.DEAL_TYPE_BALANCE:
                    balance_start_of_month += d.profit
                elif d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
                    balance_start_of_month += d.profit + d.commission + d.swap

        if balance_start_of_month <= 0:
            return 0.0

        # Growth = (balance_actuelle - balance_debut_mois) / balance_debut_mois * 100
        growth = (current_balance - balance_start_of_month) / balance_start_of_month * 100
        return growth

    def get_account_stats(self) -> AccountStats | None:
        if not self.connected and not self.connect():
            return None
        info = mt5.account_info()
        if not info:
            return None

        if info.balance > self.peak_balance:
            self.peak_balance = info.balance
        if info.equity > self.peak_equity:
            self.peak_equity = info.equity

        drawdown = max(0, self.peak_equity - info.equity)
        drawdown_pct = (drawdown / self.peak_equity * 100) if self.peak_equity > 0 else 0

        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        if drawdown_pct > self.max_drawdown_percent:
            self.max_drawdown_percent = drawdown_pct

        # Calculate deposits/withdrawals
        deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
        total_deposits = 0.0
        total_withdrawals = 0.0
        if deals:
            for d in deals:
                if d.type == mt5.DEAL_TYPE_BALANCE:
                    if d.profit > 0:
                        total_deposits += d.profit
                    else:
                        total_withdrawals += abs(d.profit)

        if self.initial_deposit == 0 and total_deposits > 0:
            self.initial_deposit = total_deposits

        net_deposit = total_deposits - total_withdrawals
        total_profit = info.balance - net_deposit if net_deposit > 0 else 0

        # Calculer la croissance depuis le début du mois
        growth = self._calculate_monthly_growth(deals, info.balance)

        # Store history point (en mémoire et dans la DB)
        now = datetime.now()
        point = HistoryPoint(
            balance=info.balance,
            equity=info.equity,
            drawdown=drawdown,
            drawdown_percent=drawdown_pct,
            timestamp=now
        )
        self.history.append(point)
        if self.current_account_id:
            history_db.save_point(point, self.current_account_id)

        return AccountStats(
            balance=info.balance,
            equity=info.equity,
            profit=total_profit,
            drawdown=drawdown,
            drawdown_percent=drawdown_pct,
            initial_deposit=self.initial_deposit,
            total_deposits=total_deposits,
            total_withdrawals=total_withdrawals,
            growth_percent=growth,
            timestamp=now
        )

    def get_trade_stats(self) -> TradeStats | None:
        if not self.connected and not self.connect():
            return None

        deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
        if not deals:
            return self._empty_trade_stats()

        trades = [d for d in deals if d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL] and d.entry == mt5.DEAL_ENTRY_OUT]

        if not trades:
            return self._empty_trade_stats()

        profits = [t.profit + t.commission + t.swap for t in trades]
        winning = [p for p in profits if p > 0]
        losing = [p for p in profits if p < 0]

        longs = [t for t in trades if t.type == mt5.DEAL_TYPE_SELL]  # Close long = SELL
        shorts = [t for t in trades if t.type == mt5.DEAL_TYPE_BUY]  # Close short = BUY
        longs_won = len([t for t in longs if (t.profit + t.commission + t.swap) > 0])
        shorts_won = len([t for t in shorts if (t.profit + t.commission + t.swap) > 0])

        gross_profit = sum(winning) if winning else 0
        gross_loss = abs(sum(losing)) if losing else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

        # Consecutive wins/losses
        max_cons_wins, max_cons_losses = self._calc_consecutive(profits)

        # Average holding time
        avg_holding = 0.0
        orders = mt5.history_orders_get(datetime(2000, 1, 1), datetime.now())
        if orders and len(orders) > 1:
            holding_times = []
            for i in range(0, len(orders) - 1, 2):
                if i + 1 < len(orders):
                    diff = orders[i + 1].time_done - orders[i].time_done
                    if diff > 0:
                        holding_times.append(diff)
            avg_holding = sum(holding_times) / len(holding_times) if holding_times else 0

        return TradeStats(
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=(len(winning) / len(trades) * 100) if trades else 0,
            best_trade=max(profits) if profits else 0,
            worst_trade=min(profits) if profits else 0,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            profit_factor=profit_factor,
            average_profit=(sum(winning) / len(winning)) if winning else 0,
            average_loss=(sum(losing) / len(losing)) if losing else 0,
            max_consecutive_wins=max_cons_wins,
            max_consecutive_losses=max_cons_losses,
            longs_count=len(longs),
            shorts_count=len(shorts),
            longs_won=longs_won,
            shorts_won=shorts_won,
            avg_holding_time_seconds=avg_holding,
            expected_payoff=(sum(profits) / len(profits)) if profits else 0
        )

    def _calc_consecutive(self, profits):
        max_wins = max_losses = current_wins = current_losses = 0
        for p in profits:
            if p > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        return max_wins, max_losses

    def _empty_trade_stats(self):
        return TradeStats(
            total_trades=0, winning_trades=0, losing_trades=0, win_rate=0,
            best_trade=0, worst_trade=0, gross_profit=0, gross_loss=0,
            profit_factor=0, average_profit=0, average_loss=0,
            max_consecutive_wins=0, max_consecutive_losses=0,
            longs_count=0, shorts_count=0, longs_won=0, shorts_won=0,
            avg_holding_time_seconds=0, expected_payoff=0
        )

    def get_risk_metrics(self) -> RiskMetrics | None:
        if not self.connected and not self.connect():
            return None
        info = mt5.account_info()
        if not info:
            return None

        current_dd = max(0, self.peak_equity - info.equity)
        current_dd_pct = (current_dd / self.peak_equity * 100) if self.peak_equity > 0 else 0

        # Deposit load
        deposit_load = (info.margin / info.equity * 100) if info.equity > 0 else 0

        # Sharpe ratio (simplified)
        sharpe = 0.0
        if len(self.history) > 10:
            returns = []
            hist = list(self.history)
            for i in range(1, len(hist)):
                if hist[i-1].equity > 0:
                    r = (hist[i].equity - hist[i-1].equity) / hist[i-1].equity
                    returns.append(r)
            if returns:
                avg_return = sum(returns) / len(returns)
                std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
                sharpe = (avg_return / std_return) if std_return > 0 else 0

        # Recovery factor
        net_profit = info.balance - self.initial_deposit if self.initial_deposit > 0 else info.profit
        recovery = (net_profit / self.max_drawdown) if self.max_drawdown > 0 else 0

        return RiskMetrics(
            max_drawdown=self.max_drawdown,
            max_drawdown_percent=self.max_drawdown_percent,
            relative_drawdown_balance=self.max_drawdown_percent,
            relative_drawdown_equity=current_dd_pct,
            max_deposit_load=deposit_load,
            sharpe_ratio=round(sharpe, 2),
            recovery_factor=round(recovery, 2),
            current_drawdown=current_dd,
            current_drawdown_percent=current_dd_pct
        )

    def get_history_trades(self, days: int = 30) -> list[Trade]:
        if not self.connected and not self.connect():
            return []

        from_date = datetime.now() - timedelta(days=days)
        deals = mt5.history_deals_get(from_date, datetime.now())
        if not deals:
            return []

        types = {0: "BUY", 1: "SELL", 2: "BALANCE", 6: "CORRECTION"}
        trades = []
        for d in deals:
            if d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
                trades.append(Trade(
                    ticket=d.ticket,
                    symbol=d.symbol,
                    type=types.get(d.type, "OTHER"),
                    volume=d.volume,
                    open_time=datetime.fromtimestamp(d.time),
                    open_price=d.price,
                    close_time=None,
                    close_price=None,
                    profit=d.profit,
                    commission=d.commission,
                    swap=d.swap,
                    comment=d.comment or ""
                ))
        return trades[-100:]  # Last 100

    def get_open_positions(self) -> list[Position]:
        if not self.connected and not self.connect():
            return []

        positions = mt5.positions_get()
        if not positions:
            return []

        result = []
        for p in positions:
            result.append(Position(
                ticket=p.ticket,
                symbol=p.symbol,
                type="BUY" if p.type == 0 else "SELL",
                volume=p.volume,
                open_time=datetime.fromtimestamp(p.time),
                open_price=p.price_open,
                current_price=p.price_current,
                profit=p.profit,
                sl=p.sl if p.sl > 0 else None,
                tp=p.tp if p.tp > 0 else None
            ))
        return result

    def get_history(self, limit: int = 60) -> list[HistoryPoint]:
        return list(self.history)[-limit:]

    def rebuild_history_from_deals(self) -> int:
        """Reconstruit l'historique balance/equity à partir des deals MT5"""
        if not self.connected and not self.connect():
            return 0

        deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
        if not deals:
            return 0

        # Trier par timestamp
        sorted_deals = sorted(deals, key=lambda d: d.time)

        running_balance = 0.0
        peak_balance = 0.0
        peak_equity = 0.0
        points_added = 0
        last_date = None

        for d in sorted_deals:
            deal_time = datetime.fromtimestamp(d.time)
            deal_date = deal_time.date()

            # Calculer le changement de balance
            if d.type == mt5.DEAL_TYPE_BALANCE:
                running_balance += d.profit
            elif d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
                # Pour les trades, ajouter profit + commission + swap
                running_balance += d.profit + d.commission + d.swap

            # Mettre à jour les peaks
            if running_balance > peak_balance:
                peak_balance = running_balance
            peak_equity = peak_balance  # Approximation: equity = balance pour l'historique

            # Calculer le drawdown
            drawdown = max(0, peak_equity - running_balance)
            drawdown_pct = (drawdown / peak_equity * 100) if peak_equity > 0 else 0

            # Sauvegarder un point par jour (pour éviter trop de données)
            if last_date != deal_date:
                point = HistoryPoint(
                    balance=running_balance,
                    equity=running_balance,  # Approximation
                    drawdown=drawdown,
                    drawdown_percent=drawdown_pct,
                    timestamp=deal_time
                )
                self.history.append(point)
                if self.current_account_id:
                    history_db.save_point(point, self.current_account_id)
                points_added += 1
                last_date = deal_date

        # Mettre à jour les valeurs du connector
        self.peak_balance = peak_balance
        self.peak_equity = peak_equity
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        if drawdown_pct > self.max_drawdown_percent:
            self.max_drawdown_percent = drawdown_pct

        logger.info("History rebuilt from MT5 deals", points_added=points_added)
        return points_added

    def get_monthly_growth(self) -> list[MonthlyGrowth]:
        if not self.connected and not self.connect():
            return []

        deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
        if not deals:
            return []

        # Group deals by month
        monthly_data: dict[tuple[int, int], float] = {}  # (year, month) -> profit
        monthly_deposits: dict[tuple[int, int], float] = {}  # Track deposits per month

        for d in deals:
            deal_time = datetime.fromtimestamp(d.time)
            key = (deal_time.year, deal_time.month)

            if d.type == mt5.DEAL_TYPE_BALANCE:
                if d.profit > 0:
                    monthly_deposits[key] = monthly_deposits.get(key, 0) + d.profit
            elif d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
                profit = d.profit + d.commission + d.swap
                monthly_data[key] = monthly_data.get(key, 0) + profit

        if not monthly_data and not monthly_deposits:
            return []

        # Get all years
        all_keys = set(monthly_data.keys()) | set(monthly_deposits.keys())
        years = sorted(set(k[0] for k in all_keys))

        # Calculate running balance for growth calculation
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        result = []

        running_balance = 0.0

        for year in years:
            months_dict: dict[str, float | None] = {}
            values_dict: dict[str, float | None] = {}
            year_growth = 0.0
            year_total_value = 0.0

            for month_idx, month_name in enumerate(month_names, 1):
                key = (year, month_idx)
                deposit = monthly_deposits.get(key, 0)
                profit = monthly_data.get(key, 0)

                if key in monthly_data or key in monthly_deposits:
                    # Add deposit to balance first
                    balance_before = running_balance + deposit
                    running_balance = balance_before + profit

                    # Store profit value
                    if key in monthly_data:
                        values_dict[month_name] = round(profit, 2)
                        year_total_value += profit
                    else:
                        values_dict[month_name] = None

                    # Calculate growth percentage for this month
                    if balance_before > 0 and key in monthly_data:
                        growth_pct = (profit / balance_before) * 100
                        months_dict[month_name] = round(growth_pct, 2)
                        year_growth += growth_pct
                    else:
                        months_dict[month_name] = None
                else:
                    months_dict[month_name] = None
                    values_dict[month_name] = None

            # Year totals
            year_total = round(year_growth, 2) if year_growth != 0 else None
            year_value = round(year_total_value, 2) if year_total_value != 0 else None

            result.append(MonthlyGrowth(
                year=year,
                months=months_dict,
                values=values_dict,
                year_total=year_total,
                year_total_value=year_value
            ))

        return result

    def get_daily_drawdown(self) -> list[DailyDrawdown]:
        """Retourne le drawdown journalier (depuis le solde de début de journée)"""
        history = list(self.history)
        if not history:
            return []

        # Grouper par jour
        daily_data: dict[str, list[HistoryPoint]] = {}
        for point in history:
            day_key = point.timestamp.strftime('%Y-%m-%d')
            if day_key not in daily_data:
                daily_data[day_key] = []
            daily_data[day_key].append(point)

        result = []
        sorted_days = sorted(daily_data.keys())
        prev_day_end_balance = None

        for day in sorted_days:
            points = daily_data[day]
            # Solde de début = fin du jour précédent ou premier point
            start_balance = prev_day_end_balance if prev_day_end_balance else points[0].balance

            # Calculer le peak et min intra-journalier
            day_peak = start_balance
            day_min = start_balance
            for p in points:
                if p.balance > day_peak:
                    day_peak = p.balance
                if p.balance < day_min:
                    day_min = p.balance

            # DD = (peak - min) / peak
            if day_peak > 0:
                dd_percent = max(0, (day_peak - day_min) / day_peak * 100)
            else:
                dd_percent = 0

            result.append(DailyDrawdown(
                date=day,
                drawdown_percent=round(dd_percent, 2),
                start_balance=round(start_balance, 2),
                min_balance=round(day_min, 2)
            ))

            prev_day_end_balance = points[-1].balance

        return result

    def get_full_dashboard(self) -> FullDashboard | None:
        account = self.get_account_info()
        stats = self.get_account_stats()
        trade_stats = self.get_trade_stats()
        risk = self.get_risk_metrics()
        positions = self.get_open_positions()
        monthly = self.get_monthly_growth()

        if not all([account, stats, trade_stats, risk]):
            return None

        return FullDashboard(
            account=account,
            stats=stats,
            trade_stats=trade_stats,
            risk_metrics=risk,
            open_positions=positions,
            monthly_growth=monthly
        )

    def reset_peak_balance(self):
        info = mt5.account_info()
        if info:
            self.peak_balance = info.balance
            self.peak_equity = info.equity

    def get_all_accounts_summary(self, use_cache: bool = True, cache_max_age: int = 60) -> list[AccountSummary]:
        """Récupère un résumé de tous les comptes configurés

        Args:
            use_cache: Utiliser le cache SQLite si disponible
            cache_max_age: Age max du cache en secondes (défaut: 60s)
        """
        # Vérifier le cache
        if use_cache and accounts_cache.is_cache_valid(cache_max_age):
            cached = accounts_cache.load_accounts()
            if cached:
                return cached

        summaries = []

        for acc_config in MT5_ACCOUNTS:
            account_id = acc_config["id"]
            account_name = acc_config["name"]
            terminal_key = acc_config.get("terminal", "roboforex")
            broker_name = "IC Markets" if terminal_key == "icmarkets" else "RoboForex"

            try:
                # Se connecter au compte
                if not self.connect(account_id):
                    # Compte non connecté
                    summaries.append(AccountSummary(
                        id=account_id,
                        name=account_name,
                        broker=broker_name,
                        server=acc_config["server"],
                        balance=0,
                        equity=0,
                        profit=0,
                        profit_percent=0,
                        drawdown=0,
                        trades=0,
                        win_rate=0,
                        currency="USD",
                        leverage=0,
                        connected=False
                    ))
                    continue

                # Récupérer les infos du compte
                info = mt5.account_info()
                if not info:
                    continue

                # Calculer les stats
                deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
                total_deposits = 0.0
                total_withdrawals = 0.0
                trades_count = 0
                winning_trades = 0

                if deals:
                    for d in deals:
                        if d.type == mt5.DEAL_TYPE_BALANCE:
                            if d.profit > 0:
                                total_deposits += d.profit
                            else:
                                total_withdrawals += abs(d.profit)
                        elif d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL] and d.entry == mt5.DEAL_ENTRY_OUT:
                            trades_count += 1
                            if (d.profit + d.commission + d.swap) > 0:
                                winning_trades += 1

                net_deposit = total_deposits - total_withdrawals
                profit = info.balance - net_deposit if net_deposit > 0 else info.profit
                profit_percent = (profit / net_deposit * 100) if net_deposit > 0 else 0

                # Calculer le drawdown
                peak = max(info.balance, info.equity)
                current_dd_pct = max(0, (peak - info.equity) / peak * 100) if peak > 0 else 0

                win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0

                summaries.append(AccountSummary(
                    id=info.login,
                    name=account_name,
                    broker=info.company or "RoboForex",
                    server=info.server,
                    balance=round(info.balance, 2),
                    equity=round(info.equity, 2),
                    profit=round(profit, 2),
                    profit_percent=round(profit_percent, 2),
                    drawdown=round(current_dd_pct, 2),
                    trades=trades_count,
                    win_rate=round(win_rate, 1),
                    currency=info.currency,
                    leverage=info.leverage,
                    connected=True
                ))

            except Exception as e:
                logger.error("Error for account", account_id=account_id, error=str(e))
                summaries.append(AccountSummary(
                    id=account_id,
                    name=account_name,
                    broker=broker_name,
                    server=acc_config["server"],
                    balance=0,
                    equity=0,
                    profit=0,
                    profit_percent=0,
                    drawdown=0,
                    trades=0,
                    win_rate=0,
                    currency="USD",
                    leverage=0,
                    connected=False
                ))

        # Sauvegarder dans le cache
        if summaries:
            accounts_cache.save_accounts(summaries)
            # Sauvegarder les snapshots pour les sparklines
            account_balance_history.save_all_snapshots(summaries)

        return summaries

    def get_global_monthly_growth(self, use_cache: bool = True, cache_max_age_hours: int = 24) -> list[dict]:
        """Récupère la croissance mensuelle agrégée de tous les comptes

        Args:
            use_cache: Utiliser le cache si disponible
            cache_max_age_hours: Age max du cache en heures (défaut: 24h)
        """
        # Vérifier le cache
        if use_cache and monthly_growth_cache.is_valid(cache_max_age_hours):
            cached = monthly_growth_cache.load()
            if cached:
                logger.debug("Monthly growth loaded from cache")
                return cached

        logger.info("Calculating monthly growth")
        from collections import defaultdict

        # Structure: {(year, month): {'profit_eur': 0, 'profit_usd': 0, 'deposit_eur': 0, 'deposit_usd': 0}}
        monthly_data: dict[tuple[int, int], dict] = defaultdict(lambda: {
            'profit_eur': 0, 'profit_usd': 0,
            'deposit_eur': 0, 'deposit_usd': 0
        })

        for acc_config in MT5_ACCOUNTS:
            account_id = acc_config["id"]

            try:
                if not self.connect(account_id):
                    continue

                info = mt5.account_info()
                if not info:
                    continue

                currency = info.currency

                deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
                if not deals:
                    continue

                running_balance = 0.0

                for d in sorted(deals, key=lambda x: x.time):
                    deal_time = datetime.fromtimestamp(d.time)
                    key = (deal_time.year, deal_time.month)

                    if d.type == mt5.DEAL_TYPE_BALANCE:
                        if d.profit > 0:
                            if currency == 'EUR':
                                monthly_data[key]['deposit_eur'] += d.profit
                            else:
                                monthly_data[key]['deposit_usd'] += d.profit
                        running_balance += d.profit
                    elif d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
                        profit = d.profit + d.commission + d.swap
                        if currency == 'EUR':
                            monthly_data[key]['profit_eur'] += profit
                        else:
                            monthly_data[key]['profit_usd'] += profit
                        running_balance += profit

            except Exception as e:
                logger.error("Monthly growth error for account", account_id=account_id, error=str(e))

        # Convertir en liste triée
        month_names = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
        years = sorted(set(k[0] for k in monthly_data.keys())) if monthly_data else []

        result = []
        for year in years:
            year_data = {
                'year': year,
                'months': {},
                'year_total_eur': 0,
                'year_total_usd': 0
            }

            for month_idx in range(1, 13):
                key = (year, month_idx)
                month_name = month_names[month_idx - 1]

                if key in monthly_data:
                    data = monthly_data[key]
                    year_data['months'][month_name] = {
                        'profit_eur': round(data['profit_eur'], 2),
                        'profit_usd': round(data['profit_usd'], 2)
                    }
                    year_data['year_total_eur'] += data['profit_eur']
                    year_data['year_total_usd'] += data['profit_usd']
                else:
                    year_data['months'][month_name] = None

            year_data['year_total_eur'] = round(year_data['year_total_eur'], 2)
            year_data['year_total_usd'] = round(year_data['year_total_usd'], 2)
            result.append(year_data)

        # Sauvegarder dans le cache
        if result:
            monthly_growth_cache.save(result)
            logger.info("Monthly growth saved", years_count=len(result))

        return result


# Global instance
mt5_connector = MT5Connector()
