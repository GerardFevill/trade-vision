"""Monthly Calculator - Preview and close month operations"""
from datetime import datetime
from db.repositories.balance_history import AccountBalanceHistory
from .elite_system import (
    get_phase, get_level_from_lot_factor,
    ELITE_DISTRIBUTION, PHASE_NAMES, PHASE_THRESHOLDS
)
from .withdrawal_calculator import calculate_standard_preview


class MonthlyCalculator:
    def __init__(self, repo):
        self.repo = repo

    def auto_close_previous_month(self, portfolio_id: int, portfolio_type: str, current_month: str):
        """Auto-close the previous month if not already closed"""
        year, month = int(current_month[:4]), int(current_month[5:7])
        if month == 1:
            prev_month = f"{year - 1}-12"
        else:
            prev_month = f"{year}-{month - 1:02d}"

        if self.repo.is_month_closed(portfolio_id, prev_month):
            return

        prev_records = self.repo.get_monthly_records(portfolio_id, prev_month)
        if not prev_records:
            return

        detail = self.repo.get_portfolio_detail(portfolio_id)
        if not detail or not detail.accounts:
            return

        is_elite = portfolio_type == "Conservateur"

        if is_elite:
            account_ids = [a.account_id for a in detail.accounts if a.account]
            balance_history = AccountBalanceHistory()
            historical_balances = balance_history.get_balances_at_month_start(account_ids, prev_month)

            manual_balances = {r["account_id"]: r["starting_balance"] for r in prev_records if r["starting_balance"]}

            ending_balances = balance_history.get_balances_at_month_start(account_ids, current_month)

            total_current = sum(ending_balances.values())
            phase = get_phase(total_current)
            phase_dist = ELITE_DISTRIBUTION.get(phase, ELITE_DISTRIBUTION[1])

            elite_accounts = []
            for a in detail.accounts:
                if not a.account:
                    continue
                acc = a.account

                if acc.id in manual_balances:
                    starting_balance = manual_balances[acc.id]
                elif acc.id in historical_balances:
                    starting_balance = historical_balances[acc.id]
                else:
                    continue

                current_balance = ending_balances.get(acc.id, starting_balance)
                monthly_profit = current_balance - starting_balance

                level = get_level_from_lot_factor(a.lot_factor)
                dist = phase_dist.get(level, [0, 1, 0])
                remun_pct, compound_pct, transfer_pct = dist

                if monthly_profit > 0:
                    remuneration = monthly_profit * remun_pct
                    compound = monthly_profit * compound_pct
                    transfer = monthly_profit * transfer_pct
                else:
                    remuneration = compound = transfer = 0

                elite_accounts.append({
                    "account_id": acc.id,
                    "account_name": acc.name,
                    "lot_factor": a.lot_factor,
                    "level": level,
                    "starting_balance": starting_balance,
                    "current_balance": current_balance,
                    "monthly_profit": monthly_profit,
                    "remuneration": remuneration,
                    "compound": compound,
                    "transfer": transfer,
                })

            if elite_accounts:
                self.repo.close_elite_month(portfolio_id, prev_month, elite_accounts)
        else:
            self.repo.close_monthly_snapshot(portfolio_id, prev_month)

    def _gather_accounts_data(self, detail, current_month):
        """Gather account data with starting balances from history or manual override"""
        account_ids = [a.account_id for a in detail.accounts if a.account]
        balance_history = AccountBalanceHistory()
        historical_balances = balance_history.get_balances_at_month_start(account_ids, current_month)

        manual_records = self.repo.get_monthly_records(detail.id, current_month)
        manual_balances = {r["account_id"]: r["starting_balance"] for r in manual_records if r["starting_balance"] is not None}

        total_starting = 0
        total_current = 0
        total_profit = 0
        accounts_data = []

        for a in detail.accounts:
            if not a.account:
                continue
            acc = a.account

            # Priority: 1) manual, 2) historical, 3) current balance
            if acc.id in manual_balances:
                starting_balance = manual_balances[acc.id]
            elif acc.id in historical_balances:
                starting_balance = historical_balances[acc.id]
            else:
                starting_balance = acc.balance

            current_balance = acc.balance
            monthly_profit = current_balance - starting_balance

            total_starting += starting_balance
            total_current += current_balance
            total_profit += monthly_profit

            accounts_data.append({
                "portfolio_account": a,
                "account": acc,
                "starting_balance": starting_balance,
                "current_balance": current_balance,
                "monthly_profit": monthly_profit,
            })

        return accounts_data, manual_balances, historical_balances, total_starting, total_current, total_profit

    def get_current_month_preview(self, portfolio, detail) -> dict:
        """Calculate current month preview with Elite or Standard distribution"""
        now = datetime.now()
        current_month = now.strftime("%Y-%m")
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        self.auto_close_previous_month(portfolio.id, portfolio.type, current_month)

        accounts_data, _, _, total_starting, total_current, total_profit = \
            self._gather_accounts_data(detail, current_month)

        is_elite = portfolio.type == "Conservateur"

        days_in_month = (month_start.replace(month=month_start.month % 12 + 1, day=1) - month_start).days if month_start.month < 12 else 31

        base = {
            "month": current_month,
            "month_start": month_start.strftime("%Y-%m-%d"),
            "current_date": now.strftime("%Y-%m-%d"),
            "days_elapsed": now.day,
            "days_in_month": days_in_month,
            "portfolio_type": portfolio.type,
            "total_starting": round(total_starting, 2),
            "total_current": round(total_current, 2),
            "total_profit": round(total_profit, 2),
            "total_profit_percent": round((total_profit / total_starting * 100) if total_starting > 0 else 0, 2),
        }

        if is_elite:
            return {**base, **self._build_elite_preview(accounts_data, total_current)}
        else:
            std = calculate_standard_preview(portfolio.type, accounts_data, detail)
            return {**base, "is_elite": False, **std}

    def _build_elite_preview(self, accounts_data, total_current) -> dict:
        """Build Elite distribution preview"""
        phase = get_phase(total_current)
        phase_name = PHASE_NAMES.get(phase, "Unknown")
        phase_dist = ELITE_DISTRIBUTION.get(phase, ELITE_DISTRIBUTION[1])

        accounts_data.sort(key=lambda x: x["portfolio_account"].lot_factor, reverse=True)

        accounts = []
        total_remuneration = 0
        total_compound = 0
        total_transfer = 0
        transfers = []
        level_order = ["N5", "N4", "N3", "N2", "N1"]
        level_profits = {}

        for data in accounts_data:
            a = data["portfolio_account"]
            acc = data["account"]
            starting_balance = data["starting_balance"]
            current_balance = data["current_balance"]
            monthly_profit = data["monthly_profit"]

            level = get_level_from_lot_factor(a.lot_factor)
            profit_pct = (monthly_profit / starting_balance * 100) if starting_balance > 0 else 0

            dist = phase_dist.get(level, [0, 1, 0])
            remun_pct, compound_pct, transfer_pct = dist

            if monthly_profit > 0:
                remuneration = monthly_profit * remun_pct
                compound = monthly_profit * compound_pct
                transfer = monthly_profit * transfer_pct
            else:
                remuneration = compound = transfer = 0

            total_remuneration += remuneration
            total_compound += compound
            total_transfer += transfer

            level_profits[level] = {
                "profit": monthly_profit,
                "transfer": transfer,
                "account_name": acc.name,
                "account_id": acc.id,
            }

            accounts.append({
                "account_id": acc.id,
                "account_name": acc.name,
                "lot_factor": a.lot_factor,
                "level": level,
                "starting_balance": round(starting_balance, 2),
                "current_balance": round(current_balance, 2),
                "monthly_profit": round(monthly_profit, 2),
                "profit_percent": round(profit_pct, 2),
                "remuneration": round(remuneration, 2),
                "remuneration_pct": remun_pct * 100,
                "compound": round(compound, 2),
                "compound_pct": compound_pct * 100,
                "transfer": round(transfer, 2),
                "transfer_pct": transfer_pct * 100,
                "currency": acc.currency
            })

        # Build transfer actions (N5 -> N4 -> N3 -> N2 -> N1)
        for i, from_level in enumerate(level_order[:-1]):
            to_level = level_order[i + 1]
            if from_level in level_profits and level_profits[from_level]["transfer"] > 0:
                transfers.append({
                    "from_level": from_level,
                    "to_level": to_level,
                    "amount": round(level_profits[from_level]["transfer"], 2),
                    "from_account": level_profits[from_level]["account_name"],
                    "from_account_id": level_profits[from_level]["account_id"],
                    "to_account": level_profits.get(to_level, {}).get("account_name", "N/A"),
                    "to_account_id": level_profits.get(to_level, {}).get("account_id"),
                })

        return {
            "is_elite": True,
            "phase": phase,
            "phase_name": phase_name,
            "phase_thresholds": f"{PHASE_THRESHOLDS[phase-1]:,} - {PHASE_THRESHOLDS[phase] if phase < 5 else '1M+':,}",
            "total_remuneration": round(total_remuneration, 2),
            "total_compound": round(total_compound, 2),
            "total_transfer": round(total_transfer, 2),
            "transfers": transfers,
            "elite_accounts": accounts
        }

    def close_current_month(self, portfolio, detail) -> dict:
        """Close current month and save distribution data"""
        now = datetime.now()
        current_month = now.strftime("%Y-%m")

        if self.repo.is_month_closed(portfolio.id, current_month):
            raise ValueError(f"Month {current_month} is already closed")

        account_ids = [a.account_id for a in detail.accounts if a.account]
        balance_history = AccountBalanceHistory()
        historical_balances = balance_history.get_balances_at_month_start(account_ids, current_month)

        manual_records = self.repo.get_monthly_records(portfolio.id, current_month)
        manual_balances = {r["account_id"]: r["starting_balance"] for r in manual_records if r["starting_balance"] is not None}

        is_elite = portfolio.type == "Conservateur"

        if is_elite:
            total_current = sum(a.account.balance for a in detail.accounts if a.account)
            phase = get_phase(total_current)
            phase_dist = ELITE_DISTRIBUTION.get(phase, ELITE_DISTRIBUTION[1])

            elite_accounts = []
            for a in detail.accounts:
                if not a.account:
                    continue
                acc = a.account

                if acc.id in manual_balances:
                    starting_balance = manual_balances[acc.id]
                elif acc.id in historical_balances:
                    starting_balance = historical_balances[acc.id]
                else:
                    starting_balance = acc.balance

                current_balance = acc.balance
                monthly_profit = current_balance - starting_balance

                level = get_level_from_lot_factor(a.lot_factor)
                dist = phase_dist.get(level, [0, 1, 0])
                remun_pct, compound_pct, transfer_pct = dist

                if monthly_profit > 0:
                    remuneration = monthly_profit * remun_pct
                    compound = monthly_profit * compound_pct
                    transfer = monthly_profit * transfer_pct
                else:
                    remuneration = compound = transfer = 0

                elite_accounts.append({
                    "account_id": acc.id,
                    "account_name": acc.name,
                    "lot_factor": a.lot_factor,
                    "level": level,
                    "starting_balance": starting_balance,
                    "current_balance": current_balance,
                    "monthly_profit": monthly_profit,
                    "remuneration": remuneration,
                    "compound": compound,
                    "transfer": transfer,
                })

            success = self.repo.close_elite_month(portfolio.id, current_month, elite_accounts)
            if not success:
                raise RuntimeError("Failed to close Elite month")

            return {
                "message": f"Month {current_month} closed successfully (Elite system)",
                "phase": phase,
                "accounts_closed": len(elite_accounts)
            }
        else:
            success = self.repo.close_monthly_snapshot(portfolio.id, current_month)
            if not success:
                raise RuntimeError("Failed to close month")

            return {
                "message": f"Month {current_month} closed successfully",
                "accounts_closed": len(detail.accounts)
            }
