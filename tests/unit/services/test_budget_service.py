"""Unit tests for budget service."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.budget_service import (
    BudgetService,
    BudgetStatus,
    get_budget_service,
    reset_budget_service,
)


class TestBudgetStatus:
    """Tests for BudgetStatus dataclass."""

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        status = BudgetStatus(
            total_budget=50.0,
            used_amount=10.0,
            remaining=40.0,
            percentage_used=20.0,
            requests_used=100,
            service_active=True,
            current_month="2026-01",
            last_updated="2026-01-24T10:00:00+00:00",
            estimated_cost_per_request=0.0063,
        )

        result = status.to_dict()

        assert result["total_budget"] == 50.0
        assert result["used_amount"] == 10.0
        assert result["remaining"] == 40.0
        assert result["percentage_used"] == 20.0
        assert result["requests_used"] == 100
        assert result["service_active"] is True
        assert result["current_month"] == "2026-01"


class TestBudgetService:
    """Tests for BudgetService class."""

    @pytest.fixture
    def temp_data_path(self, tmp_path: Path) -> Path:
        """Create temporary data path for testing."""
        return tmp_path / "budget_test.json"

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings."""
        settings = MagicMock()
        settings.budget_monthly_limit = 50.0
        settings.budget_data_path = "./data/budget_tracking.json"
        settings.budget_cost_per_llm_request = 0.0063
        return settings

    @pytest.fixture
    def budget_service(
        self, temp_data_path: Path, mock_settings: MagicMock
    ) -> BudgetService:
        """Create budget service with temporary storage."""
        with patch("app.services.budget_service.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings
            return BudgetService(data_path=temp_data_path)

    def test_initial_status(self, budget_service: BudgetService) -> None:
        """Test initial budget status."""
        status = budget_service.get_status()

        assert status.total_budget == 50.0
        assert status.used_amount == 0.0
        assert status.remaining == 50.0
        assert status.requests_used == 0
        assert status.service_active is True
        assert status.percentage_used == 0.0

    def test_record_request_success(self, budget_service: BudgetService) -> None:
        """Test recording a request successfully."""
        result = budget_service.record_request(request_type="llm")

        assert result is True

        status = budget_service.get_status()
        assert status.requests_used == 1
        assert status.used_amount > 0

    def test_record_multiple_requests(self, budget_service: BudgetService) -> None:
        """Test recording multiple requests."""
        for _ in range(10):
            budget_service.record_request(request_type="llm")

        status = budget_service.get_status()
        assert status.requests_used == 10
        assert status.used_amount == pytest.approx(0.063, rel=0.01)

    def test_record_request_with_cost_override(
        self, budget_service: BudgetService
    ) -> None:
        """Test recording a request with custom cost."""
        budget_service.record_request(request_type="llm", cost_override=1.0)

        status = budget_service.get_status()
        assert status.used_amount == 1.0

    def test_budget_threshold_blocks_service(
        self, budget_service: BudgetService
    ) -> None:
        """Test that 95% budget threshold disables service."""
        # Manually set cost near threshold
        budget_service._estimated_cost = 47.0
        budget_service._save_data()

        # This should trigger the 95% threshold (47 + 1 = 48 >= 47.5)
        result = budget_service.record_request(request_type="llm", cost_override=1.0)

        assert result is False
        assert budget_service.is_service_active() is False

    def test_service_disabled_blocks_requests(
        self, budget_service: BudgetService
    ) -> None:
        """Test that disabled service rejects new requests."""
        budget_service.disable_service()

        result = budget_service.record_request(request_type="llm")

        assert result is False

    def test_enable_service(self, budget_service: BudgetService) -> None:
        """Test enabling service after disable."""
        budget_service.disable_service()
        assert budget_service.is_service_active() is False

        budget_service.enable_service()
        assert budget_service.is_service_active() is True

    def test_disable_service(self, budget_service: BudgetService) -> None:
        """Test disabling service manually."""
        assert budget_service.is_service_active() is True

        budget_service.disable_service()
        assert budget_service.is_service_active() is False

    def test_data_persistence(
        self, temp_data_path: Path, mock_settings: MagicMock
    ) -> None:
        """Test that data persists across service instances."""
        with patch("app.services.budget_service.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings

            # Create first instance and record requests
            service1 = BudgetService(data_path=temp_data_path)
            service1.record_request(request_type="llm")
            service1.record_request(request_type="llm")

            # Create new instance - should load persisted data
            service2 = BudgetService(data_path=temp_data_path)
            status = service2.get_status()

            assert status.requests_used == 2

    def test_monthly_reset_on_new_month(
        self, temp_data_path: Path, mock_settings: MagicMock
    ) -> None:
        """Test that counters reset on new month."""
        with patch("app.services.budget_service.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings

            service = BudgetService(data_path=temp_data_path)
            service.record_request(request_type="llm")

            # Manually set to old month
            service._month = "2025-12"
            service._save_data()

            # Check status should trigger reset
            status = service.get_status()

            assert status.requests_used == 0
            assert status.used_amount == 0.0

    def test_embedding_request_cost(self, budget_service: BudgetService) -> None:
        """Test that embedding requests have lower cost."""
        budget_service.record_request(request_type="embedding")

        status = budget_service.get_status()
        # Embedding cost should be 10% of LLM cost (0.00063)
        # Note: get_status() rounds to 4 decimal places, so 0.00063 -> 0.0006
        assert status.used_amount == pytest.approx(0.0006, abs=0.0001)

    def test_get_status_percentage_calculation(
        self, budget_service: BudgetService
    ) -> None:
        """Test percentage calculation in status."""
        budget_service.record_request(request_type="llm", cost_override=25.0)

        status = budget_service.get_status()

        assert status.percentage_used == 50.0

    def test_load_corrupted_data_file(
        self, temp_data_path: Path, mock_settings: MagicMock
    ) -> None:
        """Test handling of corrupted data file."""
        # Write invalid JSON
        temp_data_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_data_path, "w") as f:
            f.write("not valid json")

        with patch("app.services.budget_service.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings

            # Should initialize with defaults
            service = BudgetService(data_path=temp_data_path)
            status = service.get_status()

            assert status.requests_used == 0
            assert status.used_amount == 0.0


class TestBudgetServiceSingleton:
    """Tests for budget service singleton functions."""

    def test_get_budget_service_returns_same_instance(self) -> None:
        """Test that get_budget_service returns singleton."""
        reset_budget_service()

        with patch("app.services.budget_service.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.budget_monthly_limit = 50.0
            mock_settings.budget_data_path = "./data/test_budget.json"
            mock_settings.budget_cost_per_llm_request = 0.0063
            mock_get_settings.return_value = mock_settings

            service1 = get_budget_service()
            service2 = get_budget_service()

            assert service1 is service2

        reset_budget_service()

    def test_reset_budget_service(self) -> None:
        """Test that reset clears the singleton."""
        reset_budget_service()

        with patch("app.services.budget_service.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.budget_monthly_limit = 50.0
            mock_settings.budget_data_path = "./data/test_budget.json"
            mock_settings.budget_cost_per_llm_request = 0.0063
            mock_get_settings.return_value = mock_settings

            service1 = get_budget_service()
            reset_budget_service()
            service2 = get_budget_service()

            assert service1 is not service2

        reset_budget_service()
