"""Unit tests for feature repository."""

import pytest
from pathlib import Path

from app.storage.models import FeatureSuggestion, FeatureStatus
from app.storage.repositories.feature_repository import FeatureRepository


class TestFeatureRepository:
    """Tests for FeatureRepository class."""

    @pytest.fixture
    def repository(self, tmp_path: Path) -> FeatureRepository:
        """Create a feature repository instance."""
        storage_path = str(tmp_path / "feature_suggestions.json")
        return FeatureRepository(storage_path=storage_path)

    @pytest.fixture
    def sample_feature(self) -> FeatureSuggestion:
        """Create a sample feature suggestion."""
        return FeatureSuggestion(
            user_email="user@example.com",
            user_name="Test User",
            title="PDF Export Feature",
            description="Add ability to export documentation as PDF"
        )

    def test_add_feature(self, repository: FeatureRepository, sample_feature: FeatureSuggestion):
        """Test adding a feature suggestion."""
        result = repository.add(sample_feature)
        assert result.id == sample_feature.id
        assert repository.count() == 1

    def test_get_feature(self, repository: FeatureRepository, sample_feature: FeatureSuggestion):
        """Test getting a feature by ID."""
        repository.add(sample_feature)
        result = repository.get(sample_feature.id)
        assert result is not None
        assert result.title == "PDF Export Feature"

    def test_get_feature_not_found(self, repository: FeatureRepository):
        """Test getting non-existent feature."""
        result = repository.get("FEAT-NOTFOUND")
        assert result is None

    def test_get_all(self, repository: FeatureRepository):
        """Test getting all features."""
        repository.add(FeatureSuggestion(title="Feature 1"))
        repository.add(FeatureSuggestion(title="Feature 2"))
        features = repository.get_all()
        assert len(features) == 2

    def test_get_open(self, repository: FeatureRepository):
        """Test getting open features."""
        f1 = FeatureSuggestion(title="Feature 1")
        f2 = FeatureSuggestion(title="Feature 2")
        f2.update_status(FeatureStatus.COMPLETED)

        repository.add(f1)
        repository.add(f2)

        open_features = repository.get_open()
        assert len(open_features) == 1
        assert open_features[0].title == "Feature 1"

    def test_get_by_status(self, repository: FeatureRepository):
        """Test getting features by status."""
        f1 = FeatureSuggestion(title="Feature 1")
        f2 = FeatureSuggestion(title="Feature 2")
        f2.update_status(FeatureStatus.PLANNED)
        f3 = FeatureSuggestion(title="Feature 3")
        f3.update_status(FeatureStatus.PLANNED)

        repository.add(f1)
        repository.add(f2)
        repository.add(f3)

        planned = repository.get_by_status(FeatureStatus.PLANNED)
        assert len(planned) == 2

    def test_get_by_user(self, repository: FeatureRepository):
        """Test getting features by user."""
        repository.add(FeatureSuggestion(user_email="user1@example.com", title="F1"))
        repository.add(FeatureSuggestion(user_email="user1@example.com", title="F2"))
        repository.add(FeatureSuggestion(user_email="user2@example.com", title="F3"))

        user1_features = repository.get_by_user("user1@example.com")
        assert len(user1_features) == 2

    def test_get_top_voted(self, repository: FeatureRepository):
        """Test getting top voted features."""
        f1 = FeatureSuggestion(title="Feature 1")
        f1.votes = 10
        f2 = FeatureSuggestion(title="Feature 2")
        f2.votes = 5
        f3 = FeatureSuggestion(title="Feature 3")
        f3.votes = 20

        repository.add(f1)
        repository.add(f2)
        repository.add(f3)

        top = repository.get_top_voted(limit=2)
        assert len(top) == 2
        assert top[0].title == "Feature 3"
        assert top[1].title == "Feature 1"

    def test_upvote(self, repository: FeatureRepository, sample_feature: FeatureSuggestion):
        """Test upvoting a feature."""
        repository.add(sample_feature)
        assert sample_feature.votes == 0

        result = repository.upvote(sample_feature.id)
        assert result is not None
        assert result.votes == 1

        result = repository.upvote(sample_feature.id)
        assert result.votes == 2

    def test_add_comment(self, repository: FeatureRepository, sample_feature: FeatureSuggestion):
        """Test adding a comment to a feature."""
        repository.add(sample_feature)

        result = repository.add_comment(
            sample_feature.id,
            "commenter@example.com",
            "This would be really useful!"
        )
        assert result is not None
        assert len(result.comments) == 1
        assert result.comments[0]["comment"] == "This would be really useful!"

    def test_update_status(self, repository: FeatureRepository, sample_feature: FeatureSuggestion):
        """Test updating feature status."""
        repository.add(sample_feature)

        result = repository.update_status(sample_feature.id, FeatureStatus.PLANNED)
        assert result is not None
        assert result.status == FeatureStatus.PLANNED.value

        result = repository.update_status(sample_feature.id, FeatureStatus.IN_PROGRESS)
        assert result.status == FeatureStatus.IN_PROGRESS.value

    def test_delete_feature(self, repository: FeatureRepository, sample_feature: FeatureSuggestion):
        """Test deleting a feature."""
        repository.add(sample_feature)
        assert repository.count() == 1
        result = repository.delete(sample_feature.id)
        assert result is True
        assert repository.count() == 0

    def test_count_open(self, repository: FeatureRepository):
        """Test counting open features."""
        f1 = FeatureSuggestion(title="Feature 1")
        f2 = FeatureSuggestion(title="Feature 2")
        f2.update_status(FeatureStatus.COMPLETED)

        repository.add(f1)
        repository.add(f2)

        assert repository.count() == 2
        assert repository.count_open() == 1

    def test_update_feature(self, repository: FeatureRepository, sample_feature: FeatureSuggestion):
        """Test updating a feature."""
        repository.add(sample_feature)
        sample_feature.description = "Updated description"
        result = repository.update(sample_feature)
        assert result is not None
        assert result.description == "Updated description"
