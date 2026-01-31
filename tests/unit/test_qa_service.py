"""Unit tests for shared QA service."""

import pytest
from unittest.mock import MagicMock, patch

from app.services.qa_service import process_question, QAResult


class TestQAResult:
    """Tests for QAResult dataclass."""

    def test_qa_result_creation(self) -> None:
        """Should create QAResult with all fields."""
        result = QAResult(
            answer="Test answer",
            sources=[{"doc_id": "1", "metadata": {}}],
            confidence=0.8,
            processing_time=1.5,
            llm_duration=1.0,
            retrieval_time=0.5,
            model="test-model",
            tokens={"prompt": 100, "completion": 50},
        )

        assert result.answer == "Test answer"
        assert result.confidence == 0.8
        assert result.processing_time == 1.5
        assert result.tokens == {"prompt": 100, "completion": 50}

    def test_qa_result_optional_tokens(self) -> None:
        """Should allow None for tokens."""
        result = QAResult(
            answer="Test",
            sources=[],
            confidence=0.5,
            processing_time=1.0,
            llm_duration=0.5,
            retrieval_time=0.5,
            model="test",
            tokens=None,
        )

        assert result.tokens is None


class TestProcessQuestion:
    """Tests for process_question function."""

    @pytest.fixture
    def mock_qa_agent(self) -> MagicMock:
        """Create mock QA agent."""
        agent = MagicMock()
        agent.answer.return_value = {
            "answer": "Mocked answer",
            "sources": [
                {
                    "doc_id": "doc1",
                    "document": "Source content",
                    "metadata": {"source": "test.md"},
                    "score": 0.9,
                }
            ],
            "confidence": 0.85,
            "processing_time": 1.5,
            "llm_duration": 1.0,
            "retrieval_time": 0.5,
            "model": "test-model",
            "tokens": {"prompt": 100, "completion": 50},
        }
        return agent

    @patch("app.services.qa_service.get_qa_agent")
    def test_process_question_basic(self, mock_get_agent: MagicMock, mock_qa_agent: MagicMock) -> None:
        """Should process question and return QAResult."""
        mock_get_agent.return_value = mock_qa_agent

        result = process_question("What is Python?")

        assert isinstance(result, QAResult)
        assert result.answer == "Mocked answer"
        assert result.confidence == 0.85
        mock_qa_agent.answer.assert_called_once_with(question="What is Python?", top_k=5)

    @patch("app.services.qa_service.get_qa_agent")
    def test_process_question_custom_top_k(self, mock_get_agent: MagicMock, mock_qa_agent: MagicMock) -> None:
        """Should pass custom top_k to agent."""
        mock_get_agent.return_value = mock_qa_agent

        process_question("Question?", top_k=10)

        mock_qa_agent.answer.assert_called_once_with(question="Question?", top_k=10)

    @patch("app.services.qa_service.get_qa_agent")
    def test_process_question_sources(self, mock_get_agent: MagicMock, mock_qa_agent: MagicMock) -> None:
        """Should include sources in result."""
        mock_get_agent.return_value = mock_qa_agent

        result = process_question("Question?")

        assert len(result.sources) == 1
        assert result.sources[0]["doc_id"] == "doc1"

    @patch("app.services.qa_service.get_qa_agent")
    def test_process_question_metrics(self, mock_get_agent: MagicMock, mock_qa_agent: MagicMock) -> None:
        """Should include all metrics in result."""
        mock_get_agent.return_value = mock_qa_agent

        result = process_question("Question?")

        assert result.processing_time == 1.5
        assert result.llm_duration == 1.0
        assert result.retrieval_time == 0.5
        assert result.model == "test-model"

    @patch("app.services.qa_service.get_qa_agent")
    def test_process_question_no_tokens(self, mock_get_agent: MagicMock, mock_qa_agent: MagicMock) -> None:
        """Should handle missing tokens in response."""
        mock_qa_agent.answer.return_value = {
            "answer": "Answer",
            "sources": [],
            "confidence": 0.5,
            "processing_time": 1.0,
            "llm_duration": 0.5,
            "retrieval_time": 0.5,
            "model": "test",
        }
        mock_get_agent.return_value = mock_qa_agent

        result = process_question("Question?")

        assert result.tokens is None

    @patch("app.services.qa_service.get_qa_agent")
    @patch("app.services.qa_service.logger")
    def test_process_question_logging(
        self, mock_logger: MagicMock, mock_get_agent: MagicMock, mock_qa_agent: MagicMock
    ) -> None:
        """Should log question processing."""
        mock_get_agent.return_value = mock_qa_agent

        process_question("What is this?", source="test")

        # Check that logging was called
        mock_logger.info.assert_called()
        call_args = [call[1] for call in mock_logger.info.call_args_list]

        # First call should be processing_question
        assert any("source" in kwargs and kwargs["source"] == "test" for kwargs in call_args)
