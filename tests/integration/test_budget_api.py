"""Integration tests for budget API endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def mock_budget_status() -> MagicMock:
    """Create a mock budget status."""
    mock_status = MagicMock()
    mock_status.total_budget = 50.0
    mock_status.used_amount = 10.5
    mock_status.remaining = 39.5
    mock_status.percentage_used = 21.0
    mock_status.requests_used = 150
    mock_status.service_active = True
    mock_status.current_month = "2026-01"
    mock_status.last_updated = "2026-01-24T10:30:00+00:00"
    mock_status.estimated_cost_per_request = 0.0063
    return mock_status


@pytest.fixture
def test_client() -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestBudgetStatusEndpoint:
    """Tests for GET /api/budget-status endpoint."""

    def test_get_budget_status_success(
        self, test_client: TestClient, mock_budget_status: MagicMock
    ) -> None:
        """Test successful budget status retrieval."""
        mock_service = MagicMock()
        mock_service.get_status.return_value = mock_budget_status

        with patch("app.api.routes.get_budget_service", return_value=mock_service):
            response = test_client.get("/api/budget-status")

        assert response.status_code == 200
        data = response.json()

        assert data["total_budget"] == 50.0
        assert data["used_amount"] == 10.5
        assert data["remaining"] == 39.5
        assert data["percentage_used"] == 21.0
        assert data["requests_used"] == 150
        assert data["service_active"] is True
        assert data["current_month"] == "2026-01"
        assert data["estimated_cost_per_request"] == 0.0063

    def test_get_budget_status_response_schema(
        self, test_client: TestClient
    ) -> None:
        """Test that response matches expected schema."""
        response = test_client.get("/api/budget-status")

        assert response.status_code == 200
        data = response.json()

        # Check all required fields are present
        required_fields = [
            "total_budget",
            "used_amount",
            "remaining",
            "percentage_used",
            "requests_used",
            "service_active",
            "current_month",
            "last_updated",
            "estimated_cost_per_request",
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_get_budget_status_service_inactive(
        self, test_client: TestClient
    ) -> None:
        """Test budget status when service is inactive."""
        mock_service = MagicMock()
        mock_status = MagicMock()
        mock_status.total_budget = 50.0
        mock_status.used_amount = 48.5
        mock_status.remaining = 1.5
        mock_status.percentage_used = 97.0
        mock_status.requests_used = 7500
        mock_status.service_active = False
        mock_status.current_month = "2026-01"
        mock_status.last_updated = "2026-01-24T10:30:00+00:00"
        mock_status.estimated_cost_per_request = 0.0063
        mock_service.get_status.return_value = mock_status

        with patch("app.api.routes.get_budget_service", return_value=mock_service):
            response = test_client.get("/api/budget-status")

            assert response.status_code == 200
            data = response.json()
            assert data["service_active"] is False
            assert data["percentage_used"] == 97.0

    def test_get_budget_status_content_type(
        self, test_client: TestClient
    ) -> None:
        """Test that response has correct content type."""
        response = test_client.get("/api/budget-status")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"


class TestBudgetStatusEdgeCases:
    """Edge case tests for budget status endpoint."""

    def test_zero_budget(self) -> None:
        """Test handling of zero budget."""
        mock_service = MagicMock()
        mock_status = MagicMock()
        mock_status.total_budget = 0.0
        mock_status.used_amount = 0.0
        mock_status.remaining = 0.0
        mock_status.percentage_used = 0.0
        mock_status.requests_used = 0
        mock_status.service_active = True
        mock_status.current_month = "2026-01"
        mock_status.last_updated = "2026-01-24T10:30:00+00:00"
        mock_status.estimated_cost_per_request = 0.0063
        mock_service.get_status.return_value = mock_status

        with patch(
            "app.api.routes.get_budget_service", return_value=mock_service
        ):
            from app.main import app
            client = TestClient(app)

            response = client.get("/api/budget-status")

            assert response.status_code == 200
            data = response.json()
            assert data["total_budget"] == 0.0

    def test_budget_exceeded(self) -> None:
        """Test handling when budget is exceeded."""
        mock_service = MagicMock()
        mock_status = MagicMock()
        mock_status.total_budget = 50.0
        mock_status.used_amount = 52.0
        mock_status.remaining = 0.0
        mock_status.percentage_used = 100.0
        mock_status.requests_used = 8000
        mock_status.service_active = False
        mock_status.current_month = "2026-01"
        mock_status.last_updated = "2026-01-24T10:30:00+00:00"
        mock_status.estimated_cost_per_request = 0.0063
        mock_service.get_status.return_value = mock_status

        with patch(
            "app.api.routes.get_budget_service", return_value=mock_service
        ):
            from app.main import app
            client = TestClient(app)

            response = client.get("/api/budget-status")

            assert response.status_code == 200
            data = response.json()
            assert data["service_active"] is False
            assert data["percentage_used"] == 100.0
            assert data["remaining"] == 0.0
