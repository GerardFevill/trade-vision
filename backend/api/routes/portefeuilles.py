"""Portfolio management routes"""
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from db.repositories import PortefeuilleRepository
from db.repositories.balance_history import AccountBalanceHistory
from services import mt5_connector
from models import (
    PortefeuilleSummary, PortefeuilleDetail,
    Portefeuille, PORTFOLIO_TYPES, LOT_FACTORS,
    MonthlySnapshot, MonthlyAccountRecord
)

router = APIRouter()
repo = PortefeuilleRepository()


# Request models
class CreatePortfolioRequest(BaseModel):
    name: str
    type: str  # "Conservateur", "Modere", "Agressif"
    client: str


class UpdatePortfolioRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None


class AddAccountRequest(BaseModel):
    account_id: int
    lot_factor: float


class UpdateWithdrawalRequest(BaseModel):
    account_id: int
    withdrawal: float
    note: Optional[str] = None


class BulkWithdrawalRequest(BaseModel):
    withdrawals: list[UpdateWithdrawalRequest]


class UpdateStartingBalanceRequest(BaseModel):
    account_id: int
    starting_balance: float


# Withdrawal percentages by portfolio type (for Modere and Agressif)
WITHDRAWAL_PERCENTAGES = {
    "Conservateur": 0.70,  # Not used - uses Elite level system instead
    "Modere": 0.80,        # 80% des gains
    "Agressif": 0.90,      # 90% des gains
}

# Elite Trading Level System (for Conservateur only)
# Mapping lot factor -> level
LOT_FACTOR_TO_LEVEL = {
    1.8: "N5",  # Highest risk
    1.4: "N4",
    1.0: "N3",
    0.6: "N2",
    0.2: "N1",  # Lowest risk
}

# Phase thresholds based on total capital
PHASE_THRESHOLDS = [0, 5000, 25000, 100000, 500000]  # Phase 1-5

# Distribution by phase and level: [remuneration, compound, transfer]
ELITE_DISTRIBUTION = {
    1: {  # Phase 1: Survie (0-5k)
        "N5": [0.10, 0.60, 0.30],
        "N4": [0.05, 0.70, 0.25],
        "N3": [0.00, 0.80, 0.20],
        "N2": [0.00, 0.90, 0.10],
        "N1": [0.00, 1.00, 0.00],
    },
    2: {  # Phase 2: Fondation (5k-25k)
        "N5": [0.15, 0.55, 0.30],
        "N4": [0.10, 0.65, 0.25],
        "N3": [0.05, 0.75, 0.20],
        "N2": [0.00, 0.85, 0.15],
        "N1": [0.00, 1.00, 0.00],
    },
    3: {  # Phase 3: Acceleration (25k-100k)
        "N5": [0.25, 0.45, 0.30],
        "N4": [0.20, 0.55, 0.25],
        "N3": [0.15, 0.65, 0.20],
        "N2": [0.10, 0.75, 0.15],
        "N1": [0.05, 0.95, 0.00],
    },
    4: {  # Phase 4: Securisation (100k-500k)
        "N5": [0.35, 0.35, 0.30],
        "N4": [0.30, 0.45, 0.25],
        "N3": [0.25, 0.55, 0.20],
        "N2": [0.20, 0.65, 0.15],
        "N1": [0.15, 0.85, 0.00],
    },
    5: {  # Phase 5: Patrimoine (500k+)
        "N5": [0.45, 0.25, 0.30],
        "N4": [0.35, 0.40, 0.25],
        "N3": [0.30, 0.70, 0.00],
        "N2": [0.25, 0.75, 0.00],
        "N1": [0.20, 0.80, 0.00],
    },
}

PHASE_NAMES = {
    1: "Survie",
    2: "Fondation",
    3: "Acceleration",
    4: "Securisation",
    5: "Patrimoine",
}


def get_phase(total_capital: float) -> int:
    """Get phase (1-5) based on total capital"""
    for i in range(4, -1, -1):
        if total_capital >= PHASE_THRESHOLDS[i]:
            return i + 1
    return 1


def get_level_from_lot_factor(lot_factor: float) -> str:
    """Map lot factor to Elite level (N5-N1)"""
    return LOT_FACTOR_TO_LEVEL.get(lot_factor, "N3")  # Default to N3


# Endpoints

@router.get("/portefeuilles/types")
async def get_portfolio_types():
    """Get available portfolio types and their lot factors"""
    return {
        "types": PORTFOLIO_TYPES,
        "all_factors": LOT_FACTORS
    }


@router.get("/portefeuilles/clients")
async def get_clients():
    """Get list of unique clients"""
    return repo.get_clients()


@router.get("/portefeuilles/used-accounts", response_model=list[int])
async def get_used_accounts() -> list[int]:
    """Get list of account IDs that are already in a portfolio"""
    return repo.get_all_used_account_ids()


@router.get("/portefeuilles", response_model=list[PortefeuilleSummary])
async def list_portfolios(
    client: Optional[str] = Query(default=None, description="Filter by client")
):
    """List all portfolios, optionally filtered by client"""
    return repo.list_portfolios(client)


@router.get("/portefeuilles/{portfolio_id}", response_model=PortefeuilleDetail)
async def get_portfolio(
    portfolio_id: int = Path(..., description="Portfolio ID")
):
    """Get detailed portfolio information with accounts"""
    detail = repo.get_portfolio_detail(portfolio_id)
    if not detail:
        raise HTTPException(404, f"Portfolio {portfolio_id} not found")
    return detail


@router.post("/portefeuilles", response_model=Portefeuille)
async def create_portfolio(request: CreatePortfolioRequest):
    """Create a new portfolio"""
    if request.type not in PORTFOLIO_TYPES:
        raise HTTPException(
            400,
            f"Invalid portfolio type. Must be one of: {list(PORTFOLIO_TYPES.keys())}"
        )

    portfolio = repo.create_portfolio(
        name=request.name,
        type=request.type,
        client=request.client
    )

    if not portfolio:
        raise HTTPException(500, "Failed to create portfolio")

    return portfolio


@router.put("/portefeuilles/{portfolio_id}", response_model=Portefeuille)
async def update_portfolio(
    portfolio_id: int = Path(..., description="Portfolio ID"),
    request: UpdatePortfolioRequest = None
):
    """Update portfolio name and/or type"""
    if request.type and request.type not in PORTFOLIO_TYPES:
        raise HTTPException(
            400,
            f"Invalid portfolio type. Must be one of: {list(PORTFOLIO_TYPES.keys())}"
        )

    success = repo.update_portfolio(
        portfolio_id,
        name=request.name,
        type=request.type
    )

    if not success:
        raise HTTPException(404, f"Portfolio {portfolio_id} not found")

    return repo.get_portfolio(portfolio_id)


@router.delete("/portefeuilles/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: int = Path(..., description="Portfolio ID")
):
    """Delete a portfolio and all its account associations"""
    success = repo.delete_portfolio(portfolio_id)
    if not success:
        raise HTTPException(404, f"Portfolio {portfolio_id} not found")
    return {"message": f"Portfolio {portfolio_id} deleted"}


@router.post("/portefeuilles/{portfolio_id}/accounts")
async def add_account_to_portfolio(
    portfolio_id: int = Path(..., description="Portfolio ID"),
    request: AddAccountRequest = None
):
    """Add an account to a portfolio with a specific lot factor"""
    # Check if portfolio exists
    portfolio = repo.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(404, f"Portfolio {portfolio_id} not found")

    # Validate lot factor for this portfolio type
    available_factors = PORTFOLIO_TYPES.get(portfolio.type, [])
    if request.lot_factor not in available_factors:
        raise HTTPException(
            400,
            f"Invalid lot factor {request.lot_factor} for portfolio type {portfolio.type}. "
            f"Available factors: {available_factors}"
        )

    # Check if account is already in another portfolio
    existing_portfolio = repo.is_account_in_portfolio(request.account_id)
    if existing_portfolio and existing_portfolio != portfolio_id:
        raise HTTPException(
            400,
            f"Account {request.account_id} is already in portfolio {existing_portfolio}"
        )

    success = repo.add_account(portfolio_id, request.account_id, request.lot_factor)
    if not success:
        raise HTTPException(500, "Failed to add account to portfolio")

    return {
        "message": f"Account {request.account_id} added to portfolio {portfolio_id} with factor {request.lot_factor}"
    }


@router.delete("/portefeuilles/{portfolio_id}/accounts/{account_id}")
async def remove_account_from_portfolio(
    portfolio_id: int = Path(..., description="Portfolio ID"),
    account_id: int = Path(..., description="Account ID")
):
    """Remove an account from a portfolio"""
    success = repo.remove_account(portfolio_id, account_id)
    if not success:
        raise HTTPException(404, f"Account {account_id} not found in portfolio {portfolio_id}")
    return {"message": f"Account {account_id} removed from portfolio {portfolio_id}"}


# Monthly Records Endpoints

@router.get("/portefeuilles/{portfolio_id}/monthly")
async def get_monthly_history(
    portfolio_id: int = Path(..., description="Portfolio ID")
):
    """Get list of months with records for a portfolio"""
    months = repo.get_monthly_history(portfolio_id)
    return {"months": months}


@router.get("/portefeuilles/{portfolio_id}/monthly/{month}")
async def get_monthly_snapshot(
    portfolio_id: int = Path(..., description="Portfolio ID"),
    month: str = Path(..., description="Month in YYYY-MM format")
):
    """Get monthly snapshot with distribution calculation"""
    portfolio = repo.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(404, f"Portfolio {portfolio_id} not found")

    records = repo.get_monthly_records(portfolio_id, month)
    if not records:
        raise HTTPException(404, f"No records found for month {month}")

    # Calculate totals and distribution
    total_starting = sum(r["starting_balance"] for r in records)
    total_ending = sum(r["ending_balance"] for r in records)
    total_profit = sum(r["profit"] for r in records)
    total_withdrawal = sum(r["withdrawal"] for r in records)
    total_profit_pct = (total_profit / total_starting * 100) if total_starting > 0 else 0

    # Get withdrawal percentage for this portfolio type
    withdrawal_pct = WITHDRAWAL_PERCENTAGES.get(portfolio.type, 0.80)
    total_weight = sum(r["lot_factor"] for r in records)

    accounts = []
    for r in records:
        weight = r["lot_factor"] / total_weight if total_weight > 0 else 0
        profit_pct = (r["profit"] / r["starting_balance"] * 100) if r["starting_balance"] > 0 else 0
        # Suggested withdrawal = profit * withdrawal_percentage
        suggested = r["profit"] * withdrawal_pct if r["profit"] > 0 else 0

        accounts.append(MonthlyAccountRecord(
            account_id=r["account_id"],
            account_name=r["account_name"],
            lot_factor=r["lot_factor"],
            starting_balance=r["starting_balance"],
            ending_balance=r["ending_balance"],
            profit=r["profit"],
            profit_percent=round(profit_pct, 2),
            weight=round(weight, 4),
            suggested_withdrawal=round(suggested, 2),
            actual_withdrawal=r["withdrawal"],
            currency=r["currency"]
        ))

    return MonthlySnapshot(
        month=month,
        total_starting=round(total_starting, 2),
        total_ending=round(total_ending, 2),
        total_profit=round(total_profit, 2),
        total_profit_percent=round(total_profit_pct, 2),
        total_withdrawal=round(total_withdrawal, 2),
        accounts=accounts,
        is_closed=total_withdrawal > 0
    )


@router.post("/portefeuilles/{portfolio_id}/monthly/{month}")
async def create_monthly_snapshot(
    portfolio_id: int = Path(..., description="Portfolio ID"),
    month: str = Path(..., description="Month in YYYY-MM format")
):
    """Create a monthly snapshot - records starting balances for the month"""
    portfolio = repo.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(404, f"Portfolio {portfolio_id} not found")

    success = repo.create_monthly_snapshot(portfolio_id, month)
    if not success:
        raise HTTPException(500, "Failed to create monthly snapshot")

    return {"message": f"Starting balances recorded for {month}"}


@router.post("/portefeuilles/{portfolio_id}/monthly/{month}/close")
async def close_monthly_snapshot(
    portfolio_id: int = Path(..., description="Portfolio ID"),
    month: str = Path(..., description="Month in YYYY-MM format")
):
    """Close a month - updates ending balances and calculates final profit"""
    portfolio = repo.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(404, f"Portfolio {portfolio_id} not found")

    success = repo.close_monthly_snapshot(portfolio_id, month)
    if not success:
        raise HTTPException(500, "Failed to close monthly snapshot")

    return {"message": f"Month {month} closed successfully"}


@router.put("/portefeuilles/{portfolio_id}/monthly/{month}")
async def update_monthly_withdrawals(
    portfolio_id: int = Path(..., description="Portfolio ID"),
    month: str = Path(..., description="Month in YYYY-MM format"),
    request: BulkWithdrawalRequest = None
):
    """Update withdrawals for multiple accounts in a month"""
    portfolio = repo.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(404, f"Portfolio {portfolio_id} not found")

    updated = 0
    for w in request.withdrawals:
        if repo.update_withdrawal(portfolio_id, month, w.account_id, w.withdrawal, w.note):
            updated += 1

    return {"message": f"Updated {updated} withdrawal records"}


@router.put("/portefeuilles/{portfolio_id}/monthly-current/starting-balance")
async def update_starting_balance(
    portfolio_id: int = Path(..., description="Portfolio ID"),
    request: UpdateStartingBalanceRequest = None
):
    """Update starting balance for an account in current month (manual override)"""
    portfolio = repo.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(404, f"Portfolio {portfolio_id} not found")

    now = datetime.now()
    current_month = now.strftime("%Y-%m")

    success = repo.update_starting_balance(
        portfolio_id, current_month, request.account_id, request.starting_balance
    )

    if not success:
        raise HTTPException(500, "Failed to update starting balance")

    return {"message": f"Starting balance updated for account {request.account_id}"}


def auto_close_previous_month(portfolio_id: int, portfolio_type: str, current_month: str):
    """Auto-close the previous month if not already closed"""
    # Calculate previous month
    year, month = int(current_month[:4]), int(current_month[5:7])
    if month == 1:
        prev_month = f"{year - 1}-12"
    else:
        prev_month = f"{year}-{month - 1:02d}"

    # Check if previous month exists and is not closed
    if repo.is_month_closed(portfolio_id, prev_month):
        return  # Already closed

    # Check if there are records for previous month
    prev_records = repo.get_monthly_records(portfolio_id, prev_month)
    if not prev_records:
        return  # No records to close

    # Get portfolio detail for closing
    detail = repo.get_portfolio_detail(portfolio_id)
    if not detail or not detail.accounts:
        return

    is_elite = portfolio_type == "Conservateur"

    if is_elite:
        # Get historical balances for previous month
        account_ids = [a.account_id for a in detail.accounts if a.account]
        balance_history = AccountBalanceHistory()
        historical_balances = balance_history.get_balances_at_month_start(account_ids, prev_month)

        # Get manual records
        manual_balances = {r["account_id"]: r["starting_balance"] for r in prev_records if r["starting_balance"]}

        # Get ending balances (start of current month = end of previous month)
        ending_balances = balance_history.get_balances_at_month_start(account_ids, current_month)

        total_current = sum(ending_balances.values())
        phase = get_phase(total_current)
        phase_dist = ELITE_DISTRIBUTION.get(phase, ELITE_DISTRIBUTION[1])

        elite_accounts = []
        for a in detail.accounts:
            if not a.account:
                continue
            acc = a.account

            # Starting balance
            if acc.id in manual_balances:
                starting_balance = manual_balances[acc.id]
            elif acc.id in historical_balances:
                starting_balance = historical_balances[acc.id]
            else:
                continue  # No data

            # Ending balance (start of current month)
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
                remuneration = 0
                compound = 0
                transfer = 0

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
            repo.close_elite_month(portfolio_id, prev_month, elite_accounts)
    else:
        repo.close_monthly_snapshot(portfolio_id, prev_month)


@router.get("/portefeuilles/{portfolio_id}/monthly-current")
async def get_current_month_preview(
    portfolio_id: int = Path(..., description="Portfolio ID")
):
    """Get current month's profit calculated automatically from 1st to today using balance history"""
    portfolio = repo.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(404, f"Portfolio {portfolio_id} not found")

    detail = repo.get_portfolio_detail(portfolio_id)
    if not detail or not detail.accounts:
        raise HTTPException(404, "No accounts in portfolio")

    # Get current month in YYYY-MM format
    now = datetime.now()
    current_month = now.strftime("%Y-%m")
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Auto-close previous month if needed
    auto_close_previous_month(portfolio_id, portfolio.type, current_month)

    # Get account IDs and fetch historical balances at month start
    account_ids = [a.account_id for a in detail.accounts if a.account]
    balance_history = AccountBalanceHistory()
    historical_balances = balance_history.get_balances_at_month_start(account_ids, current_month)

    # Check for manually set starting balances (override historical)
    manual_records = repo.get_monthly_records(portfolio_id, current_month)
    manual_balances = {r["account_id"]: r["starting_balance"] for r in manual_records if r["starting_balance"] is not None}

    # First pass: calculate totals for phase determination
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

    # Determine if this is a Conservateur portfolio using Elite level system
    is_elite = portfolio.type == "Conservateur"

    if is_elite:
        # Elite Level System for Conservateur
        phase = get_phase(total_current)
        phase_name = PHASE_NAMES.get(phase, "Unknown")
        phase_dist = ELITE_DISTRIBUTION.get(phase, ELITE_DISTRIBUTION[1])

        # Sort accounts by lot_factor descending (N5 first = highest risk)
        accounts_data.sort(key=lambda x: x["portfolio_account"].lot_factor, reverse=True)

        accounts = []
        total_remuneration = 0
        total_compound = 0
        total_transfer = 0
        transfers = []  # List of transfers between levels

        level_order = ["N5", "N4", "N3", "N2", "N1"]
        level_profits = {}  # Store profit by level for transfer calculation

        for data in accounts_data:
            a = data["portfolio_account"]
            acc = data["account"]
            starting_balance = data["starting_balance"]
            current_balance = data["current_balance"]
            monthly_profit = data["monthly_profit"]

            level = get_level_from_lot_factor(a.lot_factor)
            profit_pct = (monthly_profit / starting_balance * 100) if starting_balance > 0 else 0

            # Get distribution for this level
            dist = phase_dist.get(level, [0, 1, 0])
            remun_pct, compound_pct, transfer_pct = dist

            # Calculate distribution (only on positive profit)
            if monthly_profit > 0:
                remuneration = monthly_profit * remun_pct
                compound = monthly_profit * compound_pct
                transfer = monthly_profit * transfer_pct
            else:
                remuneration = 0
                compound = 0
                transfer = 0

            total_remuneration += remuneration
            total_compound += compound
            total_transfer += transfer

            level_profits[level] = {
                "profit": monthly_profit,
                "transfer": transfer,
                "account_name": acc.name,
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

        # Build transfer actions (N5→N4→N3→N2→N1)
        for i, from_level in enumerate(level_order[:-1]):
            to_level = level_order[i + 1]
            if from_level in level_profits and level_profits[from_level]["transfer"] > 0:
                transfers.append({
                    "from_level": from_level,
                    "to_level": to_level,
                    "amount": round(level_profits[from_level]["transfer"], 2),
                    "from_account": level_profits[from_level]["account_name"],
                    "to_account": level_profits.get(to_level, {}).get("account_name", "N/A"),
                })

        # Calculate days in month
        days_in_month = (month_start.replace(month=month_start.month % 12 + 1, day=1) - month_start).days if month_start.month < 12 else 31

        return {
            "month": current_month,
            "month_start": month_start.strftime("%Y-%m-%d"),
            "current_date": now.strftime("%Y-%m-%d"),
            "days_elapsed": now.day,
            "days_in_month": days_in_month,
            "portfolio_type": portfolio.type,
            "is_elite": True,
            "phase": phase,
            "phase_name": phase_name,
            "phase_thresholds": f"{PHASE_THRESHOLDS[phase-1]:,} - {PHASE_THRESHOLDS[phase] if phase < 5 else '1M+':,}",
            "total_starting": round(total_starting, 2),
            "total_current": round(total_current, 2),
            "total_profit": round(total_profit, 2),
            "total_profit_percent": round((total_profit / total_starting * 100) if total_starting > 0 else 0, 2),
            "total_remuneration": round(total_remuneration, 2),
            "total_compound": round(total_compound, 2),
            "total_transfer": round(total_transfer, 2),
            "transfers": transfers,
            "elite_accounts": accounts
        }

    else:
        # Standard percentage-based system for Modere and Agressif
        withdrawal_pct = WITHDRAWAL_PERCENTAGES.get(portfolio.type, 0.80)
        total_weight = sum(a.lot_factor for a in detail.accounts if a.account)

        accounts = []
        total_suggested = 0

        for data in accounts_data:
            a = data["portfolio_account"]
            acc = data["account"]
            starting_balance = data["starting_balance"]
            current_balance = data["current_balance"]
            monthly_profit = data["monthly_profit"]

            weight = a.lot_factor / total_weight if total_weight > 0 else 0
            profit_pct = (monthly_profit / starting_balance * 100) if starting_balance > 0 else 0
            suggested = monthly_profit * withdrawal_pct if monthly_profit > 0 else 0
            total_suggested += suggested

            accounts.append({
                "account_id": acc.id,
                "account_name": acc.name,
                "lot_factor": a.lot_factor,
                "starting_balance": round(starting_balance, 2),
                "current_balance": round(current_balance, 2),
                "monthly_profit": round(monthly_profit, 2),
                "profit_percent": round(profit_pct, 2),
                "weight": round(weight, 4),
                "suggested_withdrawal": round(suggested, 2),
                "currency": acc.currency
            })

        # Calculate days in month
        days_in_month = (month_start.replace(month=month_start.month % 12 + 1, day=1) - month_start).days if month_start.month < 12 else 31

        return {
            "month": current_month,
            "month_start": month_start.strftime("%Y-%m-%d"),
            "current_date": now.strftime("%Y-%m-%d"),
            "days_elapsed": now.day,
            "days_in_month": days_in_month,
            "portfolio_type": portfolio.type,
            "is_elite": False,
            "withdrawal_percentage": withdrawal_pct * 100,
            "total_starting": round(total_starting, 2),
            "total_current": round(total_current, 2),
            "total_profit": round(total_profit, 2),
            "total_profit_percent": round((total_profit / total_starting * 100) if total_starting > 0 else 0, 2),
            "total_suggested_withdrawal": round(total_suggested, 2),
            "accounts": accounts
        }


@router.post("/portefeuilles/{portfolio_id}/sync-from-mt5")
async def sync_starting_balances_from_mt5(
    portfolio_id: int = Path(..., description="Portfolio ID")
):
    """Sync starting balances from MT5 deals (accurate profit calculation)"""
    portfolio = repo.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(404, f"Portfolio {portfolio_id} not found")

    detail = repo.get_portfolio_detail(portfolio_id)
    if not detail or not detail.accounts:
        raise HTTPException(404, "No accounts in portfolio")

    now = datetime.now()
    current_month = now.strftime("%Y-%m")

    synced = []
    errors = []

    for a in detail.accounts:
        if not a.account:
            continue

        acc = a.account
        account_id = acc.id

        # Connect to MT5 for this account (config lookup is done internally)
        try:
            if mt5_connector.connect(account_id):
                result = mt5_connector.get_current_month_profit()
                if result:
                    # Update starting balance in database
                    repo.update_starting_balance(
                        portfolio_id, current_month, account_id, result["starting_balance"]
                    )
                    synced.append({
                        "account_id": account_id,
                        "account_name": acc.name,
                        "starting_balance": result["starting_balance"],
                        "profit": result["profit"],
                        "current_balance": result["current_balance"]
                    })
                else:
                    errors.append({"account_id": account_id, "error": "No profit data"})
            else:
                errors.append({"account_id": account_id, "error": "MT5 connection failed"})
        except Exception as e:
            errors.append({"account_id": account_id, "error": str(e)})

    return {
        "message": f"Synced {len(synced)} accounts",
        "synced": synced,
        "errors": errors
    }


@router.post("/portefeuilles/{portfolio_id}/monthly-current/close")
async def close_current_month(
    portfolio_id: int = Path(..., description="Portfolio ID")
):
    """Close current month and save Elite distribution data (remuneration, compound, transfer)"""
    portfolio = repo.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(404, f"Portfolio {portfolio_id} not found")

    now = datetime.now()
    current_month = now.strftime("%Y-%m")

    # Check if already closed
    if repo.is_month_closed(portfolio_id, current_month):
        raise HTTPException(400, f"Month {current_month} is already closed")

    # Get current preview data to save
    detail = repo.get_portfolio_detail(portfolio_id)
    if not detail or not detail.accounts:
        raise HTTPException(404, "No accounts in portfolio")

    # Get account IDs and fetch historical balances
    account_ids = [a.account_id for a in detail.accounts if a.account]
    balance_history = AccountBalanceHistory()
    historical_balances = balance_history.get_balances_at_month_start(account_ids, current_month)

    # Check for manual starting balances
    manual_records = repo.get_monthly_records(portfolio_id, current_month)
    manual_balances = {r["account_id"]: r["starting_balance"] for r in manual_records if r["starting_balance"] is not None}

    is_elite = portfolio.type == "Conservateur"

    if is_elite:
        # Calculate Elite distribution
        total_current = sum(a.account.balance for a in detail.accounts if a.account)
        phase = get_phase(total_current)
        phase_dist = ELITE_DISTRIBUTION.get(phase, ELITE_DISTRIBUTION[1])

        elite_accounts = []
        for a in detail.accounts:
            if not a.account:
                continue
            acc = a.account

            # Get starting balance
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
                remuneration = 0
                compound = 0
                transfer = 0

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

        success = repo.close_elite_month(portfolio_id, current_month, elite_accounts)
        if not success:
            raise HTTPException(500, "Failed to close Elite month")

        return {
            "message": f"Month {current_month} closed successfully (Elite system)",
            "phase": phase,
            "accounts_closed": len(elite_accounts)
        }
    else:
        # Standard system - just close with ending balances
        success = repo.close_monthly_snapshot(portfolio_id, current_month)
        if not success:
            raise HTTPException(500, "Failed to close month")

        return {
            "message": f"Month {current_month} closed successfully",
            "accounts_closed": len(detail.accounts)
        }


@router.get("/portefeuilles/{portfolio_id}/monthly/{month}/elite")
async def get_elite_monthly_history(
    portfolio_id: int = Path(..., description="Portfolio ID"),
    month: str = Path(..., description="Month in YYYY-MM format")
):
    """Get Elite monthly history with remuneration/compound/transfer data"""
    portfolio = repo.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(404, f"Portfolio {portfolio_id} not found")

    if portfolio.type != "Conservateur":
        raise HTTPException(400, "Elite history only available for Conservateur portfolios")

    records = repo.get_elite_monthly_records(portfolio_id, month)
    if not records:
        raise HTTPException(404, f"No Elite records found for month {month}")

    # Calculate totals
    total_starting = sum(r["starting_balance"] for r in records)
    total_ending = sum(r["ending_balance"] for r in records)
    total_profit = sum(r["profit"] for r in records)
    total_remuneration = sum(r["remuneration"] for r in records)
    total_compound = sum(r["compound"] for r in records)
    total_transfer = sum(r["transfer"] for r in records)
    is_closed = all(r["is_closed"] for r in records) if records else False

    # Build accounts with percentages
    accounts = []
    for r in records:
        profit_pct = (r["profit"] / r["starting_balance"] * 100) if r["starting_balance"] > 0 else 0
        accounts.append({
            "account_id": r["account_id"],
            "account_name": r["account_name"],
            "lot_factor": r["lot_factor"],
            "level": r["level"],
            "starting_balance": round(r["starting_balance"], 2),
            "ending_balance": round(r["ending_balance"], 2),
            "monthly_profit": round(r["profit"], 2),
            "profit_percent": round(profit_pct, 2),
            "remuneration": round(r["remuneration"], 2),
            "compound": round(r["compound"], 2),
            "transfer": round(r["transfer"], 2),
            "currency": r["currency"]
        })

    return {
        "month": month,
        "is_closed": is_closed,
        "total_starting": round(total_starting, 2),
        "total_ending": round(total_ending, 2),
        "total_profit": round(total_profit, 2),
        "total_profit_percent": round((total_profit / total_starting * 100) if total_starting > 0 else 0, 2),
        "total_remuneration": round(total_remuneration, 2),
        "total_compound": round(total_compound, 2),
        "total_transfer": round(total_transfer, 2),
        "accounts": accounts
    }
