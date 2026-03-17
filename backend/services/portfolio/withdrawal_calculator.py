"""Withdrawal Calculator - Standard percentage-based withdrawal for non-Elite portfolios"""

# Withdrawal percentages by portfolio type
WITHDRAWAL_PERCENTAGES = {
    "Securise": 0.50,      # 50% des gains
    "Conservateur": 0.70,  # Not used directly - uses Elite level system
    "Modere": 0.80,        # 80% des gains
    "Agressif": 0.90,      # 90% des gains
}


def calculate_standard_preview(portfolio_type: str, accounts_data: list, detail) -> dict:
    """Calculate standard withdrawal preview for Modere/Agressif portfolios"""
    withdrawal_pct = WITHDRAWAL_PERCENTAGES.get(portfolio_type, 0.80)
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

    return {
        "withdrawal_percentage": withdrawal_pct * 100,
        "total_suggested_withdrawal": round(total_suggested, 2),
        "accounts": accounts
    }
