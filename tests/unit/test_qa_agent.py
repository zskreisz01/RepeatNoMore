"""Unit tests for QA agent."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.agents.qa_agent import QAAgent, get_qa_agent
from app.llm import LLMResponse, TokenUsage


@pytest.fixture
def mock_retriever():
    """Mock retriever for testing."""
    with patch("app.agents.qa_agent.get_retriever") as mock:
        retriever = Mock()
        retriever.retrieve_with_context.return_value = {
            "context": "Python is a high-level programming language.",
            "sources": [
                {
                    "doc_id": "doc_1",
                    "document": "Python is a programming language.",
                    "metadata": {"source": "python.md"},
                    "score": 0.95
                }
            ],
            "num_documents": 1
        }
        mock.return_value = retriever
        yield retriever


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider."""
    with patch("app.agents.qa_agent.get_llm_provider") as mock:
        provider = Mock()
        provider.provider_name = "mock"
        provider.model_name = "mock-model"
        provider.chat.return_value = LLMResponse(
            content="Python is a high-level, interpreted programming language.",
            model="mock-model",
            provider="mock",
            tokens=TokenUsage(prompt_tokens=50, completion_tokens=20, total_tokens=70),
            duration=0.5
        )
        mock.return_value = provider
        yield provider


class TestQAAgent:
    """Test cases for QA Agent."""

    @pytest.fixture
    def agent(self, mock_retriever, mock_llm_provider):
        """Create QA agent for testing."""
        return QAAgent()

    def test_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent is not None
        assert agent.settings is not None
        assert agent.retriever is not None
        assert agent.system_prompt is not None

    def test_build_system_prompt(self, agent):
        """Test system prompt generation."""
        prompt = agent._build_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "RepeatNoMore" in prompt
        assert "documentation" in prompt.lower()

    def test_format_context(self, agent):
        """Test context formatting."""
        context = "Sample context"
        sources = [
            {"metadata": {"source": "test1.md"}},
            {"metadata": {"source": "test2.md"}}
        ]

        formatted = agent._format_context(context, sources)

        assert "Documentation Context" in formatted
        assert "Sample context" in formatted
        assert "Sources" in formatted
        assert "test1.md" in formatted
        assert "test2.md" in formatted

    def test_build_prompt(self, agent):
        """Test prompt building."""
        question = "What is Python?"
        context = "Python is a programming language."

        prompt = agent._build_prompt(question, context)

        assert isinstance(prompt, str)
        assert question in prompt
        assert context in prompt
        assert "Question" in prompt

    def test_answer_success(self, agent, mock_retriever, mock_llm_provider):
        """Test successful question answering."""
        question = "What is Python?"

        result = agent.answer(question)

        assert "answer" in result
        assert "sources" in result
        assert "confidence" in result
        assert "processing_time" in result

        assert isinstance(result["answer"], str)
        assert len(result["answer"]) > 0
        assert 0 <= result["confidence"] <= 1
        assert result["processing_time"] > 0

        # Verify retriever was called
        mock_retriever.retrieve_with_context.assert_called_once()

        # Verify LLM provider was called
        mock_llm_provider.chat.assert_called_once()

    def test_answer_empty_question(self, agent):
        """Test that empty question raises ValueError."""
        with pytest.raises(ValueError, match="Question cannot be empty"):
            agent.answer("")

        with pytest.raises(ValueError, match="Question cannot be empty"):
            agent.answer("   ")

    def test_answer_with_custom_parameters(self, agent, mock_retriever, mock_llm_provider):
        """Test answering with custom parameters."""
        result = agent.answer(
            question="What is Python?",
            top_k=3,
            temperature=0.5,
            max_tokens=500
        )

        assert "answer" in result

        # Verify retriever was called with correct top_k
        call_kwargs = mock_retriever.retrieve_with_context.call_args[1]
        assert call_kwargs.get("top_k") == 3

        # Verify LLM provider was called with correct parameters
        call_args = mock_llm_provider.chat.call_args
        messages, options = call_args[0]  # positional args
        assert options.temperature == 0.5
        assert options.max_tokens == 500

    def test_answer_no_sources(self, agent, mock_retriever, mock_llm_provider):
        """Test answering when no sources are found."""
        # Mock retriever to return no sources
        mock_retriever.retrieve_with_context.return_value = {
            "context": "No relevant information found.",
            "sources": [],
            "num_documents": 0
        }

        result = agent.answer("What is obscure topic?")

        assert "answer" in result
        assert result["confidence"] == 0.3  # Low confidence
        assert len(result["sources"]) == 0

    def test_answer_high_confidence(self, agent, mock_retriever, mock_llm_provider):
        """Test confidence calculation with high-scoring sources."""
        # Mock retriever with high-scoring sources
        mock_retriever.retrieve_with_context.return_value = {
            "context": "Test context",
            "sources": [
                {"doc_id": "1", "document": "Doc 1", "metadata": {}, "score": 0.95},
                {"doc_id": "2", "document": "Doc 2", "metadata": {}, "score": 0.93}
            ],
            "num_documents": 2
        }

        result = agent.answer("Test question")

        # Average score should be (0.95 + 0.93) / 2 = 0.94
        assert result["confidence"] > 0.9
        assert result["confidence"] <= 0.95  # Capped at 0.95

    def test_answer_retrieval_failure(self, agent, mock_retriever):
        """Test handling of retrieval failure."""
        mock_retriever.retrieve_with_context.side_effect = Exception("Retrieval error")

        with pytest.raises(RuntimeError, match="Failed to generate answer"):
            agent.answer("Test question")

    def test_answer_llm_failure(self, agent, mock_retriever, mock_llm_provider):
        """Test handling of LLM failure."""
        mock_llm_provider.chat.side_effect = Exception("LLM error")

        with pytest.raises(RuntimeError, match="Failed to generate answer"):
            agent.answer("Test question")

    def test_stream_answer_not_implemented(self, agent):
        """Test that stream_answer is not yet implemented."""
        with pytest.raises(NotImplementedError, match="Streaming not yet implemented"):
            agent.stream_answer("Test question")

    def test_get_qa_agent_singleton(self, mock_retriever, mock_llm_provider):
        """Test that get_qa_agent returns same instance."""
        # Clear global instance
        import app.agents.qa_agent
        app.agents.qa_agent._qa_agent = None

        agent1 = get_qa_agent()
        agent2 = get_qa_agent()

        assert agent1 is agent2

    def test_answer_with_sources_list(self, agent, mock_retriever, mock_llm_provider):
        """Test that sources are properly returned."""
        mock_retriever.retrieve_with_context.return_value = {
            "context": "Context",
            "sources": [
                {
                    "doc_id": "doc_1",
                    "document": "Document 1",
                    "metadata": {"source": "file1.md"},
                    "score": 0.9
                },
                {
                    "doc_id": "doc_2",
                    "document": "Document 2",
                    "metadata": {"source": "file2.md"},
                    "score": 0.8
                }
            ],
            "num_documents": 2
        }

        result = agent.answer("Test question")

        assert len(result["sources"]) == 2
        assert result["sources"][0]["doc_id"] == "doc_1"
        assert result["sources"][1]["doc_id"] == "doc_2"

    def test_answer_processing_time(self, agent, mock_retriever, mock_llm_provider):
        """Test that processing time is measured."""
        result = agent.answer("Test question")

        assert "processing_time" in result
        assert result["processing_time"] > 0
        assert isinstance(result["processing_time"], float)


class TestQAAgentPromptFormatting:
    """Test cases for prompt formatting."""

    @pytest.fixture
    def agent(self, mock_retriever, mock_llm_provider):
        """Create QA agent for testing."""
        return QAAgent()

    def test_context_includes_sources(self, agent):
        """Test that formatted context includes source information."""
        context = "Test content"
        sources = [
            {"metadata": {"source": "doc1.md"}},
            {"metadata": {"source": "doc2.md"}}
        ]

        formatted = agent._format_context(context, sources)

        assert "doc1.md" in formatted
        assert "doc2.md" in formatted
        assert "1." in formatted
        assert "2." in formatted

    def test_context_with_missing_source(self, agent):
        """Test formatting when source metadata is missing."""
        context = "Test"
        sources = [{"metadata": {}}]  # No source field

        formatted = agent._format_context(context, sources)

        assert "Unknown" in formatted

    def test_prompt_structure(self, agent):
        """Test that prompt has expected structure."""
        question = "What is testing?"
        context = "Testing is important."

        prompt = agent._build_prompt(question, context)

        assert "Question" in prompt
        assert "Instructions" in prompt
        assert question in prompt
        assert context in prompt
