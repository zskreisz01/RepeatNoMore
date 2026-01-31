"""Budget tracking service for RepeatNoMore application.

This module provides budget tracking and cost estimation for LLM requests,
enabling cost control and budget management for the application.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BudgetStatus:
    """Budget status data."""

    total_budget: float
    used_amount: float
    remaining: float
    percentage_used: float
    requests_used: int
    service_active: bool
    current_month: str
    last_updated: str
    estimated_cost_per_request: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class BudgetService:
    """Service for tracking and managing budget usage.

    Tracks request counts, estimates costs based on configured rates,
    and enforces budget limits by disabling service when threshold is reached.
    """

    BUDGET_THRESHOLD_PERCENT = 95  # Disable service at 95% usage

    def __init__(self, data_path: Optional[Path] = None) -> None:
        """
        Initialize budget service.

        Args:
            data_path: Path to store budget data file. If None, uses config setting.
        """
        self.settings = get_settings()
        self.data_path = data_path or Path(self.settings.budget_data_path)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        self._load_data()
        logger.info("budget_service_initialized", data_path=str(self.data_path))

    def _load_data(self) -> None:
        """Load budget data from persistent storage."""
        if self.data_path.exists():
            try:
                with open(self.data_path) as f:
                    data = json.load(f)
                    self._requests_count = data.get("requests_count", 0)
                    self._estimated_cost = data.get("estimated_cost", 0.0)
                    self._month = data.get("month", self._current_month())
                    self._service_disabled = data.get("service_disabled", False)

                    # Reset if new month
                    if self._month != self._current_month():
                        self._reset_monthly()
            except Exception as e:
                logger.error("budget_data_load_failed", error=str(e))
                self._init_defaults()
        else:
            self._init_defaults()

    def _init_defaults(self) -> None:
        """Initialize default values."""
        self._requests_count = 0
        self._estimated_cost = 0.0
        self._month = self._current_month()
        self._service_disabled = False

    def _save_data(self) -> None:
        """Save budget data to persistent storage."""
        try:
            data = {
                "requests_count": self._requests_count,
                "estimated_cost": self._estimated_cost,
                "month": self._month,
                "service_disabled": self._service_disabled,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.data_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("budget_data_save_failed", error=str(e))

    @staticmethod
    def _current_month() -> str:
        """Get current month string (YYYY-MM)."""
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def _reset_monthly(self) -> None:
        """Reset monthly counters."""
        logger.info(
            "budget_monthly_reset",
            old_month=self._month,
            old_requests=self._requests_count,
            old_cost=self._estimated_cost,
        )
        self._requests_count = 0
        self._estimated_cost = 0.0
        self._month = self._current_month()
        self._service_disabled = False
        self._save_data()

    def record_request(
        self,
        request_type: str = "llm",
        cost_override: Optional[float] = None,
    ) -> bool:
        """
        Record a request and update estimated cost.

        Args:
            request_type: Type of request ('llm', 'embedding', 'other')
            cost_override: Override the default cost estimation

        Returns:
            bool: True if request was recorded, False if budget exceeded
        """
        # Check if new month
        if self._month != self._current_month():
            self._reset_monthly()

        # Check if service is disabled
        if self._service_disabled:
            logger.warning("budget_request_blocked", reason="service_disabled")
            return False

        # Calculate cost
        if cost_override is not None:
            cost = cost_override
        elif request_type == "llm":
            cost = self.settings.budget_cost_per_llm_request
        elif request_type == "embedding":
            cost = self.settings.budget_cost_per_llm_request * 0.1  # Embeddings are ~10% of LLM cost
        else:
            cost = self.settings.budget_cost_per_llm_request

        # Check budget threshold
        budget_limit = self.settings.budget_monthly_limit
        threshold = budget_limit * (self.BUDGET_THRESHOLD_PERCENT / 100)

        if self._estimated_cost + cost >= threshold:
            logger.warning(
                "budget_threshold_reached",
                current_cost=self._estimated_cost,
                threshold=threshold,
                limit=budget_limit,
            )
            self._service_disabled = True
            self._save_data()
            return False

        # Record the request
        self._requests_count += 1
        self._estimated_cost += cost
        self._save_data()

        logger.debug(
            "budget_request_recorded",
            request_type=request_type,
            cost=cost,
            total_cost=self._estimated_cost,
            total_requests=self._requests_count,
        )

        return True

    def get_status(self) -> BudgetStatus:
        """
        Get current budget status.

        Returns:
            BudgetStatus: Current budget status including usage and limits
        """
        # Check if new month
        if self._month != self._current_month():
            self._reset_monthly()

        budget_limit = self.settings.budget_monthly_limit
        remaining = max(0, budget_limit - self._estimated_cost)
        percentage = (self._estimated_cost / budget_limit * 100) if budget_limit > 0 else 0

        return BudgetStatus(
            total_budget=budget_limit,
            used_amount=round(self._estimated_cost, 4),
            remaining=round(remaining, 4),
            percentage_used=round(percentage, 2),
            requests_used=self._requests_count,
            service_active=not self._service_disabled,
            current_month=self._month,
            last_updated=datetime.now(timezone.utc).isoformat(),
            estimated_cost_per_request=self.settings.budget_cost_per_llm_request,
        )

    def enable_service(self) -> None:
        """Re-enable the service (admin operation)."""
        self._service_disabled = False
        self._save_data()
        logger.info("budget_service_enabled")

    def disable_service(self) -> None:
        """Disable the service (budget exceeded or manual)."""
        self._service_disabled = True
        self._save_data()
        logger.info("budget_service_disabled")

    def is_service_active(self) -> bool:
        """
        Check if service is active (not budget-blocked).

        Returns:
            bool: True if service is active and accepting requests
        """
        if self._month != self._current_month():
            self._reset_monthly()
        return not self._service_disabled


# Global instance
_budget_service: Optional[BudgetService] = None


def get_budget_service() -> BudgetService:
    """
    Get or create a global budget service instance.

    Returns:
        BudgetService: The budget service singleton
    """
    global _budget_service
    if _budget_service is None:
        _budget_service = BudgetService()
    return _budget_service


def reset_budget_service() -> None:
    """Reset the global budget service instance (useful for testing)."""
    global _budget_service
    _budget_service = None
