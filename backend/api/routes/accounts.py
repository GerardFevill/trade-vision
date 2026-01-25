"""Account management routes"""
from fastapi import APIRouter, HTTPException, Query, Path
from services import mt5_connector, sync_service
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


@router.post("/accounts/{account_id}/rebuild-history")
async def rebuild_account_history(account_id: int = Path(..., description="ID du compte MT5")):
    """Reconstruit l'historique balance/equity complet depuis les deals MT5"""
    # Se connecter au compte
    if not mt5_connector.connect(account_id):
        raise HTTPException(503, f"Impossible de se connecter au compte {account_id}")

    # Reconstruire l'historique
    points_added = mt5_connector.rebuild_history_from_deals()

    return {
        "message": f"Historique reconstruit pour compte {account_id}",
        "points_added": points_added,
        "account_id": account_id
    }


@router.post("/accounts/{account_id}/sync")
async def sync_account(
    account_id: int = Path(..., description="ID du compte MT5"),
    force: bool = Query(default=False, description="Forcer la sync même si pas de changement")
):
    """Synchronise les données d'un compte vers la DB (uniquement si changements détectés)"""
    # Se connecter au compte
    if not mt5_connector.connect(account_id):
        raise HTTPException(503, f"Impossible de se connecter au compte {account_id}")

    # Synchroniser
    synced = sync_service.sync_account(account_id, force=force)

    return {
        "message": f"Compte {account_id} {'synchronisé' if synced else 'pas de changement'}",
        "synced": synced,
        "account_id": account_id
    }


@router.post("/sync/all")
async def sync_all_accounts(
    force: bool = Query(default=False, description="Forcer la sync même si pas de changement")
):
    """Synchronise tous les comptes vers la DB (uniquement ceux avec des changements)"""
    # Lancer en arrière-plan pour ne pas bloquer
    def do_sync():
        return sync_service.sync_all_accounts(force=force)

    thread = threading.Thread(target=do_sync, daemon=True)
    thread.start()

    return {
        "message": "Synchronisation lancée en arrière-plan",
        "force": force
    }


@router.get("/sync/status")
async def get_sync_status():
    """Vérifie quels comptes ont besoin d'être synchronisés"""
    return sync_service.quick_check_all()
