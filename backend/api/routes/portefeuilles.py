"""Portfolio management routes - v2"""
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from db.repositories import PortefeuilleRepository
from services import mt5_connector
from services.portfolio import (
    WITHDRAWAL_PERCENTAGES, get_phase, get_level_from_lot_factor,
    MonthlyCalculator
)
from models import (
    PortefeuilleSummary, PortefeuilleDetail,
    Portefeuille, PORTFOLIO_TYPES, LOT_FACTORS,
    MonthlySnapshot, MonthlyAccountRecord
)

router = APIRouter()
repo = PortefeuilleRepository()
monthly_calc = MonthlyCalculator(repo)


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
    lot_factor: Optional[float] = None  # Optional for Securise portfolios


class UpdateWithdrawalRequest(BaseModel):
    account_id: int
    withdrawal: float
    note: Optional[str] = None


class BulkWithdrawalRequest(BaseModel):
    withdrawals: list[UpdateWithdrawalRequest]


class UpdateStartingBalanceRequest(BaseModel):
    account_id: int
    starting_balance: float


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
    portfolio = repo.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(404, f"Portfolio {portfolio_id} not found")

    available_factors = PORTFOLIO_TYPES.get(portfolio.type, [])

    if portfolio.type == "Securise":
        lot_factor = 1.0
    else:
        if request.lot_factor is None:
            raise HTTPException(400, f"lot_factor is required for portfolio type {portfolio.type}")
        if request.lot_factor not in available_factors:
            raise HTTPException(
                400,
                f"Invalid lot factor {request.lot_factor} for portfolio type {portfolio.type}. "
                f"Available factors: {available_factors}"
            )
        lot_factor = request.lot_factor

    existing_portfolio = repo.is_account_in_portfolio(request.account_id)
    if existing_portfolio and existing_portfolio != portfolio_id:
        raise HTTPException(
            400,
            f"Account {request.account_id} is already in portfolio {existing_portfolio}"
        )

    success = repo.add_account(portfolio_id, request.account_id, lot_factor)
    if not success:
        raise HTTPException(500, "Failed to add account to portfolio")

    return {
        "message": f"Account {request.account_id} added to portfolio {portfolio_id}"
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

    withdrawal_pct = WITHDRAWAL_PERCENTAGES.get(portfolio.type, 0.80)
    total_weight = sum(r["lot_factor"] for r in records)

    accounts = []
    for r in records:
        weight = r["lot_factor"] / total_weight if total_weight > 0 else 0
        profit_pct = (r["profit"] / r["starting_balance"] * 100) if r["starting_balance"] > 0 else 0
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


@router.get("/portefeuilles/{portfolio_id}/monthly-current")
async def get_current_month_preview(
    portfolio_id: int = Path(..., description="Portfolio ID")
):
    """Get current month's profit calculated automatically from 1st to today"""
    portfolio = repo.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(404, f"Portfolio {portfolio_id} not found")

    detail = repo.get_portfolio_detail(portfolio_id)
    if not detail or not detail.accounts:
        raise HTTPException(404, "No accounts in portfolio")

    return monthly_calc.get_current_month_preview(portfolio, detail)


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

        try:
            if mt5_connector.connect(account_id):
                result = mt5_connector.get_current_month_profit()
                if result:
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
    """Close current month and save Elite distribution data"""
    portfolio = repo.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(404, f"Portfolio {portfolio_id} not found")

    detail = repo.get_portfolio_detail(portfolio_id)
    if not detail or not detail.accounts:
        raise HTTPException(404, "No accounts in portfolio")

    try:
        return monthly_calc.close_current_month(portfolio, detail)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))


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

    total_starting = sum(r["starting_balance"] for r in records)
    total_ending = sum(r["ending_balance"] for r in records)
    total_profit = sum(r["profit"] for r in records)
    total_remuneration = sum(r["remuneration"] for r in records)
    total_compound = sum(r["compound"] for r in records)
    total_transfer = sum(r["transfer"] for r in records)
    is_closed = all(r["is_closed"] for r in records) if records else False

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
