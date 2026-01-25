"""Pytest configuration and fixtures"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def test_client():
    """Create a test client for the FastAPI app"""
    from main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_alert():
    """Sample alert data for testing"""
    return {
        "account_id": 12345,
        "alert_type": "drawdown",
        "condition": "above",
        "threshold": 10.0,
        "message": "Test alert"
    }


@pytest.fixture
def sample_trade():
    """Sample trade data for testing"""
    return {
        "ticket": 123456,
        "symbol": "EURUSD",
        "type": "BUY",
        "volume": 0.1,
        "open_time": "2024-01-01T10:00:00",
        "open_price": 1.1000,
        "close_time": "2024-01-01T11:00:00",
        "close_price": 1.1050,
        "profit": 50.0,
        "commission": -0.5,
        "swap": 0.0,
        "comment": ""
    }
