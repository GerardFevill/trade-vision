"""MT5 Monitor API - Entry Point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from services import mt5_connector
from api import api_router
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - connect/disconnect MT5"""
    mt5_connector.connect()
    yield
    mt5_connector.disconnect()


app = FastAPI(
    title="MT5 Monitor API",
    version="2.0.0",
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
