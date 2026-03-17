"""MT5 Monthly Growth Service - Monthly and global growth calculations"""
from datetime import datetime
from collections import defaultdict
from models import MonthlyGrowth
from db import monthly_growth_cache
from config import MT5_ACCOUNTS
from config.logging import logger
from .shared_state import MT5SharedState


class MonthlyGrowthService:
    def __init__(self, state: MT5SharedState, mt5, connect_fn=None):
        self.state = state
        self.mt5 = mt5
        self.connect_fn = connect_fn

    def get_monthly_growth(self) -> list[MonthlyGrowth]:
        mt5 = self.mt5

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

        all_keys = set(monthly_data.keys()) | set(monthly_deposits.keys())
        years = sorted(set(k[0] for k in all_keys))

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
                    balance_before = running_balance + deposit
                    running_balance = balance_before + profit

                    if key in monthly_data:
                        values_dict[month_name] = round(profit, 2)
                        year_total_value += profit
                    else:
                        values_dict[month_name] = None

                    if balance_before > 0 and key in monthly_data:
                        growth_pct = (profit / balance_before) * 100
                        months_dict[month_name] = round(growth_pct, 2)
                        year_growth += growth_pct
                    else:
                        months_dict[month_name] = None
                else:
                    months_dict[month_name] = None
                    values_dict[month_name] = None

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

    def get_global_monthly_growth(self, use_cache: bool = True, cache_max_age_hours: int = 24) -> list[dict]:
        if use_cache and monthly_growth_cache.is_valid(cache_max_age_hours):
            cached = monthly_growth_cache.load()
            if cached:
                logger.debug("Monthly growth loaded from cache")
                return cached

        logger.info("Calculating monthly growth")
        mt5 = self.mt5

        monthly_data: dict[tuple[int, int], dict] = defaultdict(lambda: {
            'profit_eur': 0, 'profit_usd': 0,
            'deposit_eur': 0, 'deposit_usd': 0
        })

        for acc_config in MT5_ACCOUNTS:
            account_id = acc_config["id"]

            try:
                if self.connect_fn and not self.connect_fn(account_id):
                    continue

                info = mt5.account_info()
                if not info:
                    continue

                currency = info.currency

                deals = mt5.history_deals_get(datetime(2000, 1, 1), datetime.now())
                if not deals:
                    continue

                for d in sorted(deals, key=lambda x: x.time):
                    deal_time = datetime.fromtimestamp(d.time)
                    key = (deal_time.year, deal_time.month)

                    if d.type == mt5.DEAL_TYPE_BALANCE:
                        if d.profit > 0:
                            if currency == 'EUR':
                                monthly_data[key]['deposit_eur'] += d.profit
                            else:
                                monthly_data[key]['deposit_usd'] += d.profit
                    elif d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
                        profit = d.profit + d.commission + d.swap
                        if currency == 'EUR':
                            monthly_data[key]['profit_eur'] += profit
                        else:
                            monthly_data[key]['profit_usd'] += profit

            except Exception as e:
                logger.error("Monthly growth error for account", account_id=account_id, error=str(e))

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

        if result:
            monthly_growth_cache.save(result)
            logger.info("Monthly growth saved", years_count=len(result))

        return result
