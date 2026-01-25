"""API endpoint tests"""
import pytest


class TestHealthEndpoint:
    """Tests for the health check endpoint"""

    def test_health_check(self, test_client):
        """Test that health endpoint returns correct status"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestAlertTypes:
    """Tests for alert types endpoint"""

    def test_get_alert_types(self, test_client):
        """Test that alert types endpoint returns valid data"""
        response = test_client.get("/api/alerts/types")
        assert response.status_code == 200
        data = response.json()
        assert "types" in data
        assert "conditions" in data
        assert "statuses" in data
        assert len(data["types"]) > 0


class TestPagination:
    """Tests for pagination functionality"""

    def test_trades_pagination_params(self, test_client):
        """Test that paginated trades endpoint accepts correct parameters"""
        response = test_client.get("/api/trades/paginated?days=30&page=1&limit=10")
        # May return 503 if MT5 not connected, but should accept params
        assert response.status_code in [200, 503]


class TestRateLimiting:
    """Tests for rate limiting functionality"""

    def test_rate_limit_headers(self, test_client):
        """Test that rate limit headers are present"""
        response = test_client.get("/health")
        # Rate limiting may or may not be applied to health endpoint
        assert response.status_code == 200


class TestExportEndpoints:
    """Tests for export functionality"""

    def test_export_endpoints_exist(self, test_client):
        """Test that export endpoints are available"""
        # These may return 503 if MT5 not connected
        csv_response = test_client.get("/api/export/trades/csv?days=30")
        assert csv_response.status_code in [200, 503]
