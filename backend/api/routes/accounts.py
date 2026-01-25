"""Account management routes"""
from fastapi import APIRouter, HTTPException, Query, Path
from services import mt5_connector
from db import accounts_cache
from models import AccountSummary
import threading

router = APIRouter()


@router.get("/accounts", response_model=list[AccountSummary])
async def get_all_accounts(
    refresh: bool = Query(default=False, description="Forcer le rafraîchissement du cache")
):
    """Récupère la liste de tous les comptes (toujours depuis le cache, rafraîchissement en arrière-plan)"""
    # Toujours retourner le cache d'abord (même ancien)
    cached = accounts_cache.load_accounts()

    # Si refresh demandé ou cache vide, rafraîchir
    if refresh or not cached:
        # Si cache vide, on doit attendre
        if not cached:
            return mt5_connector.get_all_accounts_summary(use_cache=False)
        # Sinon rafraîchir en arrière-plan
        threading.Thread(target=mt5_connector.get_all_accounts_summary, args=(False,), daemon=True).start()

    return cached if cached else []


@router.post("/accounts/{account_id}/connect")
async def connect_to_account(account_id: int = Path(..., description="ID du compte MT5")):
    """Se connecte à un compte spécifique"""
    success = mt5_connector.connect(account_id)
    if not success:
        raise HTTPException(503, f"Impossible de se connecter au compte {account_id}")
    return {"message": f"Connecté au compte {account_id}", "account_id": account_id}


@router.post("/accounts/{account_id}/reset-peaks")
async def reset_account_peaks(account_id: int = Path(..., description="ID du compte MT5")):
    """Réinitialise les peaks (balance/equity) pour un compte - remet le drawdown à zéro"""
    # Forcer la reconnexion pour recharger l'historique
    mt5_connector.current_account_id = None
    if not mt5_connector.connect(account_id):
        raise HTTPException(503, f"Impossible de se connecter au compte {account_id}")

    # Reset les peaks aux valeurs actuelles
    mt5_connector.reset_peak_balance()
    mt5_connector.max_drawdown = 0.0
    mt5_connector.max_drawdown_percent = 0.0

    return {
        "message": f"Peaks réinitialisés pour compte {account_id}",
        "peak_balance": mt5_connector.peak_balance,
        "peak_equity": mt5_connector.peak_equity
    }
