"""Elite Monitor API - Entry Point"""
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from services import mt5_connector, ctrader_connector
from api import api_router
from config.settings import settings
from config.logging import logger

__version__ = "1.0.0"


def _connect_brokers():
    """Connect to brokers in background thread to avoid blocking API startup"""
    try:
        mt5_connector.connect()
    except Exception as e:
        logger.warning("MT5 connection failed (will retry on demand)", error=str(e))
    try:
        ctrader_connector.connect()
    except Exception as e:
        logger.warning("cTrader connection failed (will retry on demand)", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - connect brokers in background, API available immediately"""
    bg = threading.Thread(target=_connect_brokers, daemon=True)
    bg.start()
    yield
    ctrader_connector.disconnect()
    mt5_connector.disconnect()


app = FastAPI(
    title="Elite Monitor API",
    description="Multi-broker Trading Accounts Monitoring",
    version=__version__,
    lifespan=lifespan
)

# CORS middleware - origins from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.api_host, port=settings.api_port, reload=True)
