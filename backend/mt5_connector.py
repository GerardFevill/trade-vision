import MetaTrader5 as mt5
from datetime import datetime, timedelta
from collections import deque
from models import (
    AccountInfo, AccountStats, TradeStats, RiskMetrics,
    Trade, Position, HistoryPoint, ConnectionStatus, FullDashboard, MonthlyGrowth, MonthlyDrawdown,
    DailyDrawdown, WeeklyDrawdown, YearlyDrawdown
)
from database import history_db


class MT5Connector:
    def __init__(self, history_max_size: int = 3600):
        self.connected = False
        self.peak_balance = 0.0
        self.peak_equity = 0.0
        self.initial_deposit = 0.0
        self.history: deque[HistoryPoint] = deque(maxlen=history_max_size)
        self.max_drawdown = 0.0
        self.max_drawdown_percent = 0.0
        self._load_history_from_db()

    def _load_history_from_db(self):
        """Charge l'historique depuis la base de données au démarrage"""
        db_history = history_db.load_history(days=730)  # Charger 2 ans d'historique
        for point in db_history:
            self.history.append(point)
        if db_history:
            # Restaurer peak values depuis l'historique
            self.peak_balance = max(p.balance for p in db_history)
            self.peak_equity = max(p.equity for p in db_history)
            self.max_drawdown = max(p.drawdown for p in db_history)
            self.max_drawdown_percent = max(p.drawdown_percent for p in db_history)
            print(f"Historique chargé: {len(db_history)} points")
        else:
            # DB vide - reconstruire depuis les deals MT5
            print("Base de données vide, reconstruction depuis les deals MT5...")
            self.rebuild_history_from_deals()

    def connect(self) -> bool:
        if not mt5.initialize():
            return False
        self.connected = True
        info = mt5.account_info()
        if info:
            # Ne pas écraser les peaks si on a des données historiques plus hautes
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
        growth = ((info.balance - net_deposit) / net_deposit * 100) if net_deposit > 0 else 0

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
        history_db.save_point(point)

        return AccountStats(
            balance=info.balance,
            equity=info.equity,
            profit=info.profit,
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
                history_db.save_point(point)
                points_added += 1
                last_date = deal_date

        # Mettre à jour les valeurs du connector
        self.peak_balance = peak_balance
        self.peak_equity = peak_equity
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        if drawdown_pct > self.max_drawdown_percent:
            self.max_drawdown_percent = drawdown_pct

        print(f"Historique reconstruit: {points_added} points depuis les deals MT5")
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

    def get_monthly_drawdown(self) -> list[MonthlyDrawdown]:
        """Retourne le MAX des drawdowns journaliers par mois"""
        # Récupérer les DD journaliers
        daily_dd = self.get_daily_drawdown()
        if not daily_dd:
            return []

        from datetime import datetime as dt

        # Grouper par mois
        monthly_max: dict[tuple[int, int], float] = {}  # (year, month) -> max drawdown %

        for d in daily_dd:
            date_obj = dt.strptime(d.date, '%Y-%m-%d')
            key = (date_obj.year, date_obj.month)
            if key not in monthly_max or d.drawdown_percent > monthly_max[key]:
                monthly_max[key] = d.drawdown_percent

        if not monthly_max:
            return []

        # Get all years
        years = sorted(set(k[0] for k in monthly_max.keys()))
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        result = []

        for year in years:
            months_dict: dict[str, float | None] = {}
            year_max_dd = 0.0

            for month_idx, month_name in enumerate(month_names, 1):
                key = (year, month_idx)
                if key in monthly_max:
                    dd = round(monthly_max[key], 2)
                    months_dict[month_name] = dd
                    if dd > year_max_dd:
                        year_max_dd = dd
                else:
                    months_dict[month_name] = None

            result.append(MonthlyDrawdown(
                year=year,
                months=months_dict,
                year_max=round(year_max_dd, 2) if year_max_dd > 0 else None
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

    def get_weekly_drawdown(self) -> list[WeeklyDrawdown]:
        """Retourne le MAX des drawdowns journaliers par semaine"""
        # Récupérer les DD journaliers
        daily_dd = self.get_daily_drawdown()
        if not daily_dd:
            return []

        # Grouper par semaine
        from datetime import datetime as dt
        weekly_max: dict[tuple[int, int], tuple[float, str]] = {}  # (year, week) -> (max_dd, start_date)

        for d in daily_dd:
            date_obj = dt.strptime(d.date, '%Y-%m-%d')
            year, week, _ = date_obj.isocalendar()
            key = (year, week)

            if key not in weekly_max:
                weekly_max[key] = (d.drawdown_percent, d.date)
            else:
                current_max, current_date = weekly_max[key]
                if d.drawdown_percent > current_max:
                    weekly_max[key] = (d.drawdown_percent, current_date)
                # Garder la première date de la semaine
                if d.date < current_date:
                    weekly_max[key] = (weekly_max[key][0], d.date)

        result = []
        for (year, week), (max_dd, start_date) in sorted(weekly_max.items()):
            result.append(WeeklyDrawdown(
                year=year,
                week=week,
                start_date=start_date,
                drawdown_percent=round(max_dd, 2)
            ))

        return result

    def get_yearly_drawdown(self) -> list[YearlyDrawdown]:
        """Retourne le MAX des drawdowns journaliers par année"""
        # Récupérer les DD journaliers
        daily_dd = self.get_daily_drawdown()
        if not daily_dd:
            return []

        from datetime import datetime as dt

        # Grouper par année
        yearly_data: dict[int, list[DailyDrawdown]] = {}
        for d in daily_dd:
            date_obj = dt.strptime(d.date, '%Y-%m-%d')
            year = date_obj.year
            if year not in yearly_data:
                yearly_data[year] = []
            yearly_data[year].append(d)

        result = []
        sorted_years = sorted(yearly_data.keys())

        for year in sorted_years:
            days = yearly_data[year]
            max_dd = max(d.drawdown_percent for d in days)
            start_balance = days[0].start_balance
            min_balance = min(d.min_balance for d in days)

            result.append(YearlyDrawdown(
                year=year,
                drawdown_percent=round(max_dd, 2),
                start_balance=round(start_balance, 2),
                min_balance=round(min_balance, 2)
            ))

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


mt5_connector = MT5Connector()
