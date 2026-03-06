"""Trade Vision API - Entry Point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from services import mt5_connector, ctrader_connector
from api import api_router
from config.settings import settings

__version__ = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - connect/disconnect MT5 and cTrader"""
    mt5_connector.connect()
    ctrader_connector.connect()
    yield
    ctrader_connector.disconnect()
    mt5_connector.disconnect()


app = FastAPI(
    title="Trade Vision API",
    description="MT5 Trading Accounts Monitoring Dashboard",
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
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
