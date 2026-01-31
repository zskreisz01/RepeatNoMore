"""Repository for feature suggestion storage operations."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.storage.json_storage import JSONStorage
from app.storage.models import FeatureSuggestion, FeatureStatus
from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class FeatureRepository:
    """Repository for managing feature suggestions."""

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize feature repository.

        Args:
            storage_path: Optional custom path for storage file
        """
        if storage_path is None:
            settings = get_settings()
            base_path = Path(settings.docs_repo_path).parent.parent / "data" / "storage"
            storage_path = str(base_path / "feature_suggestions.json")

        self.storage = JSONStorage[FeatureSuggestion](
            storage_path, collection_name="features"
        )
        logger.info("feature_repository_initialized", path=storage_path)

    def add(self, feature: FeatureSuggestion) -> FeatureSuggestion:
        """
        Add a new feature suggestion.

        Args:
            feature: The feature suggestion to add

        Returns:
            The added feature with ID
        """
        self.storage.add(feature.to_dict())
        logger.info("feature_added", id=feature.id, user=feature.user_email)
        return feature

    def get(self, feature_id: str) -> Optional[FeatureSuggestion]:
        """
        Get a feature by ID.

        Args:
            feature_id: The feature ID

        Returns:
            The feature if found, None otherwise
        """
        data = self.storage.get_by_id(feature_id)
        if data:
            return FeatureSuggestion.from_dict(data)
        return None

    def get_all(self) -> list[FeatureSuggestion]:
        """Get all feature suggestions."""
        items = self.storage.get_all()
        return [FeatureSuggestion.from_dict(item) for item in items]

    def get_open(self) -> list[FeatureSuggestion]:
        """Get all open feature suggestions."""
        items = self.storage.query({"status": FeatureStatus.OPEN.value})
        return [FeatureSuggestion.from_dict(item) for item in items]

    def get_by_status(self, status: FeatureStatus) -> list[FeatureSuggestion]:
        """Get all features with a specific status."""
        items = self.storage.query({"status": status.value})
        return [FeatureSuggestion.from_dict(item) for item in items]

    def get_by_user(self, user_email: str) -> list[FeatureSuggestion]:
        """Get all features suggested by a specific user."""
        items = self.storage.query({"user_email": user_email})
        return [FeatureSuggestion.from_dict(item) for item in items]

    def get_top_voted(self, limit: int = 10) -> list[FeatureSuggestion]:
        """
        Get top voted feature suggestions.

        Args:
            limit: Maximum number of features to return

        Returns:
            List of features sorted by votes descending
        """
        features = self.get_all()
        features.sort(key=lambda f: f.votes, reverse=True)
        return features[:limit]

    def update(self, feature: FeatureSuggestion) -> Optional[FeatureSuggestion]:
        """
        Update an existing feature.

        Args:
            feature: The feature with updated values

        Returns:
            The updated feature if found, None otherwise
        """
        result = self.storage.update(feature.id, feature.to_dict())
        if result:
            logger.info("feature_updated", id=feature.id, status=feature.status)
            return FeatureSuggestion.from_dict(result)
        return None

    def upvote(self, feature_id: str) -> Optional[FeatureSuggestion]:
        """
        Upvote a feature suggestion.

        Args:
            feature_id: The feature ID

        Returns:
            The updated feature if found, None otherwise
        """
        feature = self.get(feature_id)
        if feature:
            feature.upvote()
            return self.update(feature)
        return None

    def add_comment(
        self, feature_id: str, user_email: str, comment: str
    ) -> Optional[FeatureSuggestion]:
        """
        Add a comment to a feature suggestion.

        Args:
            feature_id: The feature ID
            user_email: Email of the commenter
            comment: The comment text

        Returns:
            The updated feature if found, None otherwise
        """
        feature = self.get(feature_id)
        if feature:
            feature.add_comment(user_email, comment)
            return self.update(feature)
        return None

    def update_status(
        self, feature_id: str, status: FeatureStatus
    ) -> Optional[FeatureSuggestion]:
        """
        Update the status of a feature.

        Args:
            feature_id: The feature ID
            status: The new status

        Returns:
            The updated feature if found, None otherwise
        """
        feature = self.get(feature_id)
        if feature:
            feature.update_status(status)
            return self.update(feature)
        return None

    def delete(self, feature_id: str) -> bool:
        """
        Delete a feature suggestion.

        Args:
            feature_id: The feature ID

        Returns:
            True if deleted, False if not found
        """
        return self.storage.delete(feature_id)

    def count(self) -> int:
        """Get total feature count."""
        return self.storage.count()

    def count_open(self) -> int:
        """Get count of open features."""
        return len(self.get_open())


# Global instance
_feature_repository: Optional[FeatureRepository] = None


@lru_cache()
def get_feature_repository() -> FeatureRepository:
    """
    Get or create a global feature repository instance.

    Returns:
        FeatureRepository: The feature repository
    """
    global _feature_repository
    if _feature_repository is None:
        _feature_repository = FeatureRepository()
    return _feature_repository
