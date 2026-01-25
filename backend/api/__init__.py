"""API module"""
from fastapi import APIRouter
from .routes import accounts, dashboard, analytics, trades, drawdown

# Main API router
api_router = APIRouter(prefix="/api")

# Include all route modules
api_router.include_router(accounts.router, tags=["accounts"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(analytics.router, tags=["analytics"])
api_router.include_router(trades.router, tags=["trades"])
api_router.include_router(drawdown.router, tags=["drawdown"])

__all__ = ['api_router']
