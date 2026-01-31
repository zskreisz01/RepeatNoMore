"""Unit tests for storage models."""

import pytest
from datetime import datetime

from app.storage.models import (
    DraftUpdate,
    DraftStatus,
    PendingQuestion,
    QuestionStatus,
    FeatureSuggestion,
    FeatureStatus,
    AcceptedQA,
    Language,
)


class TestDraftUpdate:
    """Tests for DraftUpdate model."""

    def test_create_draft_generates_id(self):
        """Test that creating a draft generates a unique ID."""
        draft = DraftUpdate(
            user_email="user@example.com",
            content="Test content",
            target_section="getting_started.md"
        )
        assert draft.id.startswith("DRAFT-")
        assert len(draft.id) == 14  # DRAFT- (6 chars) + 8 hex chars

    def test_create_draft_with_defaults(self):
        """Test default values for new draft."""
        draft = DraftUpdate()
        assert draft.status == DraftStatus.PENDING.value
        assert draft.language == Language.EN.value
        assert draft.approved_by is None
        assert draft.applied_at is None

    def test_draft_to_dict(self):
        """Test serialization to dictionary."""
        draft = DraftUpdate(
            user_email="user@example.com",
            content="Test content",
            target_section="getting_started.md"
        )
        data = draft.to_dict()
        assert data["user_email"] == "user@example.com"
        assert data["content"] == "Test content"
        assert data["status"] == DraftStatus.PENDING.value

    def test_draft_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "id": "DRAFT-12345678",
            "user_email": "user@example.com",
            "user_name": "Test User",
            "content": "Test content",
            "target_section": "getting_started.md",
            "description": "Test description",
            "language": "en",
            "status": "pending",
            "created_at": "2025-01-23T10:00:00",
            "updated_at": "2025-01-23T10:00:00",
            "approved_by": None,
            "applied_at": None,
            "rejection_reason": None,
            "metadata": {}
        }
        draft = DraftUpdate.from_dict(data)
        assert draft.id == "DRAFT-12345678"
        assert draft.user_email == "user@example.com"

    def test_draft_approve(self):
        """Test approving a draft."""
        draft = DraftUpdate(user_email="user@example.com")
        draft.approve("admin@example.com")
        assert draft.status == DraftStatus.APPROVED.value
        assert draft.approved_by == "admin@example.com"

    def test_draft_reject(self):
        """Test rejecting a draft."""
        draft = DraftUpdate(user_email="user@example.com")
        draft.reject("Invalid content")
        assert draft.status == DraftStatus.REJECTED.value
        assert draft.rejection_reason == "Invalid content"

    def test_draft_mark_applied(self):
        """Test marking a draft as applied."""
        draft = DraftUpdate(user_email="user@example.com")
        draft.mark_applied()
        assert draft.status == DraftStatus.APPLIED.value
        assert draft.applied_at is not None


class TestPendingQuestion:
    """Tests for PendingQuestion model."""

    def test_create_question_generates_id(self):
        """Test that creating a question generates a unique ID."""
        question = PendingQuestion(
            user_email="user@example.com",
            question="How do I install?",
            bot_answer="Run pip install..."
        )
        assert question.id.startswith("Q-")
        assert len(question.id) == 10  # Q- + 8 chars

    def test_create_question_with_defaults(self):
        """Test default values for new question."""
        question = PendingQuestion()
        assert question.status == QuestionStatus.ESCALATED.value
        assert question.platform == "api"
        assert question.admin_response is None

    def test_question_to_dict(self):
        """Test serialization to dictionary."""
        question = PendingQuestion(
            user_email="user@example.com",
            question="Test question",
            bot_answer="Test answer"
        )
        data = question.to_dict()
        assert data["user_email"] == "user@example.com"
        assert data["question"] == "Test question"

    def test_question_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "id": "Q-12345678",
            "user_email": "user@example.com",
            "user_name": "Test User",
            "question": "Test question",
            "bot_answer": "Test answer",
            "rejection_reason": None,
            "language": "en",
            "status": "escalated",
            "platform": "discord",
            "conversation_id": None,
            "created_at": "2025-01-23T10:00:00",
            "updated_at": "2025-01-23T10:00:00",
            "admin_response": None,
            "responded_by": None,
            "responded_at": None,
            "metadata": {}
        }
        question = PendingQuestion.from_dict(data)
        assert question.id == "Q-12345678"
        assert question.platform == "discord"

    def test_question_respond(self):
        """Test responding to a question."""
        question = PendingQuestion(question="Test?", bot_answer="Answer")
        question.respond("admin@example.com", "Correct answer")
        assert question.status == QuestionStatus.ANSWERED.value
        assert question.admin_response == "Correct answer"
        assert question.responded_by == "admin@example.com"
        assert question.responded_at is not None

    def test_question_put_on_hold(self):
        """Test putting a question on hold."""
        question = PendingQuestion(question="Test?")
        question.put_on_hold()
        assert question.status == QuestionStatus.ON_HOLD.value


class TestFeatureSuggestion:
    """Tests for FeatureSuggestion model."""

    def test_create_feature_generates_id(self):
        """Test that creating a feature generates a unique ID."""
        feature = FeatureSuggestion(
            user_email="user@example.com",
            title="New Feature",
            description="Feature description"
        )
        assert feature.id.startswith("FEAT-")
        assert len(feature.id) == 13  # FEAT- + 8 chars

    def test_create_feature_with_defaults(self):
        """Test default values for new feature."""
        feature = FeatureSuggestion()
        assert feature.status == FeatureStatus.OPEN.value
        assert feature.votes == 0
        assert feature.comments == []

    def test_feature_to_dict(self):
        """Test serialization to dictionary."""
        feature = FeatureSuggestion(
            user_email="user@example.com",
            title="Test Feature",
            description="Test description"
        )
        data = feature.to_dict()
        assert data["user_email"] == "user@example.com"
        assert data["title"] == "Test Feature"

    def test_feature_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "id": "FEAT-12345678",
            "user_email": "user@example.com",
            "user_name": "Test User",
            "title": "Test Feature",
            "description": "Test description",
            "language": "en",
            "status": "open",
            "created_at": "2025-01-23T10:00:00",
            "updated_at": "2025-01-23T10:00:00",
            "votes": 5,
            "comments": [],
            "metadata": {}
        }
        feature = FeatureSuggestion.from_dict(data)
        assert feature.id == "FEAT-12345678"
        assert feature.votes == 5

    def test_feature_upvote(self):
        """Test upvoting a feature."""
        feature = FeatureSuggestion(title="Test")
        assert feature.votes == 0
        feature.upvote()
        assert feature.votes == 1
        feature.upvote()
        assert feature.votes == 2

    def test_feature_add_comment(self):
        """Test adding a comment to a feature."""
        feature = FeatureSuggestion(title="Test")
        feature.add_comment("user@example.com", "Great idea!")
        assert len(feature.comments) == 1
        assert feature.comments[0]["user_email"] == "user@example.com"
        assert feature.comments[0]["comment"] == "Great idea!"
        assert "created_at" in feature.comments[0]

    def test_feature_update_status(self):
        """Test updating feature status."""
        feature = FeatureSuggestion(title="Test")
        feature.update_status(FeatureStatus.PLANNED)
        assert feature.status == FeatureStatus.PLANNED.value


class TestAcceptedQA:
    """Tests for AcceptedQA model."""

    def test_create_qa_generates_id(self):
        """Test that creating a Q&A generates a unique ID."""
        qa = AcceptedQA(
            question="How to install?",
            answer="Use pip install..."
        )
        assert qa.id.startswith("QA-")

    def test_qa_to_markdown(self):
        """Test converting Q&A to markdown format."""
        qa = AcceptedQA(
            question="How do I install the framework?",
            answer="Run `pip install repeatnomore`.",
            created_at="2025-01-23T10:00:00"
        )
        markdown = qa.to_markdown()
        assert "### How do I install the framework?" in markdown
        assert "Run `pip install repeatnomore`." in markdown
        assert "Accepted on 2025-01-23" in markdown


class TestLanguageEnum:
    """Tests for Language enum."""

    def test_language_values(self):
        """Test language enum values."""
        assert Language.EN.value == "en"
        assert Language.HU.value == "hu"


class TestStatusEnums:
    """Tests for status enums."""

    def test_draft_status_values(self):
        """Test DraftStatus enum values."""
        assert DraftStatus.PENDING.value == "pending"
        assert DraftStatus.APPROVED.value == "approved"
        assert DraftStatus.REJECTED.value == "rejected"
        assert DraftStatus.APPLIED.value == "applied"

    def test_question_status_values(self):
        """Test QuestionStatus enum values."""
        assert QuestionStatus.PENDING.value == "pending"
        assert QuestionStatus.ANSWERED.value == "answered"
        assert QuestionStatus.ESCALATED.value == "escalated"
        assert QuestionStatus.ON_HOLD.value == "on_hold"

    def test_feature_status_values(self):
        """Test FeatureStatus enum values."""
        assert FeatureStatus.OPEN.value == "open"
        assert FeatureStatus.PLANNED.value == "planned"
        assert FeatureStatus.COMPLETED.value == "completed"
