"""Dashboard routes - status, account info, full dashboard"""
from fastapi import APIRouter, HTTPException
from services import mt5_connector
from models import ConnectionStatus, AccountInfo, FullDashboard

router = APIRouter()


@router.get("/status", response_model=ConnectionStatus)
async def get_status():
    """Get MT5 connection status"""
    return mt5_connector.get_connection_status()


@router.get("/account", response_model=AccountInfo)
async def get_account():
    """Get current account information"""
    data = mt5_connector.get_account_info()
    if not data:
        raise HTTPException(503, "MT5 unavailable")
    return data


@router.get("/dashboard", response_model=FullDashboard)
async def get_dashboard():
    """Get full dashboard with all account data"""
    data = mt5_connector.get_full_dashboard()
    if not data:
        raise HTTPException(503, "MT5 unavailable")
    return data
