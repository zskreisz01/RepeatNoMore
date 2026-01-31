"""Unit tests for Discord embed formatters."""

import pytest
import discord

from app.discord.embeds import (
    create_answer_embed,
    create_error_embed,
    create_search_embed,
    create_help_embed,
)
from app.services.qa_service import QAResult


class TestCreateAnswerEmbed:
    """Tests for answer embed creation."""

    @pytest.fixture
    def sample_result(self) -> QAResult:
        """Create a sample QAResult for testing."""
        return QAResult(
            answer="This is the answer to your question.",
            sources=[
                {
                    "doc_id": "1",
                    "document": "Source document content",
                    "metadata": {"source": "docs/test.md"},
                    "score": 0.9,
                }
            ],
            confidence=0.85,
            processing_time=1.5,
            llm_duration=1.0,
            retrieval_time=0.5,
            model="mistral:7b-instruct",
            tokens={"prompt": 100, "completion": 50},
        )

    def test_create_answer_embed_basic(self, sample_result: QAResult) -> None:
        """Should create valid answer embed."""
        embed = create_answer_embed("Test question?", sample_result)

        assert embed.title == "RepeatNoMore Answer"
        assert embed.description == "This is the answer to your question."
        assert len(embed.fields) >= 1

    def test_create_answer_embed_question_field(self, sample_result: QAResult) -> None:
        """Should include question in field."""
        embed = create_answer_embed("What is Python?", sample_result)

        question_field = next(f for f in embed.fields if f.name == "Question")
        assert question_field.value == "What is Python?"

    def test_create_answer_embed_sources_field(self, sample_result: QAResult) -> None:
        """Should include sources in field."""
        embed = create_answer_embed("Question?", sample_result)

        sources_field = next(f for f in embed.fields if f.name == "Sources")
        assert "docs/test.md" in sources_field.value

    def test_create_answer_embed_footer(self, sample_result: QAResult) -> None:
        """Should include confidence and timing in footer."""
        embed = create_answer_embed("Question?", sample_result)

        assert embed.footer is not None
        assert "85%" in embed.footer.text
        assert "1.50s" in embed.footer.text
        assert "mistral:7b-instruct" in embed.footer.text

    def test_create_answer_embed_high_confidence_emoji(
        self, sample_result: QAResult
    ) -> None:
        """Should show green emoji for high confidence."""
        sample_result.confidence = 0.8
        embed = create_answer_embed("Question?", sample_result)

        assert embed.footer is not None
        assert "\U0001f7e2" in embed.footer.text  # Green circle

    def test_create_answer_embed_medium_confidence_emoji(
        self, sample_result: QAResult
    ) -> None:
        """Should show yellow emoji for medium confidence."""
        sample_result.confidence = 0.5
        embed = create_answer_embed("Question?", sample_result)

        assert embed.footer is not None
        assert "\U0001f7e1" in embed.footer.text  # Yellow circle

    def test_create_answer_embed_low_confidence_emoji(
        self, sample_result: QAResult
    ) -> None:
        """Should show red emoji for low confidence."""
        sample_result.confidence = 0.3
        embed = create_answer_embed("Question?", sample_result)

        assert embed.footer is not None
        assert "\U0001f534" in embed.footer.text  # Red circle

    def test_create_answer_embed_long_answer(self) -> None:
        """Should handle long answers by truncating."""
        long_result = QAResult(
            answer="x" * 5000,
            sources=[],
            confidence=0.5,
            processing_time=1.0,
            llm_duration=0.5,
            retrieval_time=0.5,
            model="test",
            tokens=None,
        )
        embed = create_answer_embed("Question?", long_result)

        # Should be truncated to 4096 or less
        assert embed.description is not None
        assert len(embed.description) <= 4096
        assert embed.description.endswith("...")

    def test_create_answer_embed_long_question(self, sample_result: QAResult) -> None:
        """Should truncate long questions."""
        long_question = "x" * 2000
        embed = create_answer_embed(long_question, sample_result)

        question_field = next(f for f in embed.fields if f.name == "Question")
        assert len(question_field.value) <= 1024

    def test_create_answer_embed_no_sources(self) -> None:
        """Should handle results with no sources."""
        result = QAResult(
            answer="Answer without sources",
            sources=[],
            confidence=0.5,
            processing_time=1.0,
            llm_duration=0.5,
            retrieval_time=0.5,
            model="test",
            tokens=None,
        )
        embed = create_answer_embed("Question?", result)

        # Should not have sources field
        sources_fields = [f for f in embed.fields if f.name == "Sources"]
        assert len(sources_fields) == 0

    def test_create_answer_embed_custom_color(self, sample_result: QAResult) -> None:
        """Should accept custom color."""
        embed = create_answer_embed(
            "Question?", sample_result, color=discord.Color.green()
        )
        assert embed.color == discord.Color.green()


class TestCreateErrorEmbed:
    """Tests for error embed creation."""

    def test_create_error_embed_basic(self) -> None:
        """Should create valid error embed."""
        embed = create_error_embed("Something went wrong")

        assert embed.title == "Error"
        assert "Something went wrong" in embed.description
        assert embed.color == discord.Color.red()

    def test_create_error_embed_long_message(self) -> None:
        """Should truncate long error messages."""
        long_error = "x" * 2000
        embed = create_error_embed(long_error)

        assert embed.description is not None
        # Should be truncated (1000 chars + formatting)
        assert len(embed.description) < 1100

    def test_create_error_embed_footer(self) -> None:
        """Should include helpful footer."""
        embed = create_error_embed("Error")

        assert embed.footer is not None
        assert "try again" in embed.footer.text.lower()

    def test_create_error_embed_custom_color(self) -> None:
        """Should accept custom color."""
        embed = create_error_embed("Error", color=discord.Color.orange())
        assert embed.color == discord.Color.orange()


class TestCreateSearchEmbed:
    """Tests for search results embed creation."""

    def test_create_search_embed_with_results(self) -> None:
        """Should create embed with search results."""
        results = [
            ("doc1", "First document content", {"source": "docs/first.md"}),
            ("doc2", "Second document content", {"source": "docs/second.md"}),
        ]
        embed = create_search_embed("test query", results)

        assert "test query" in embed.title
        assert len(embed.fields) == 2

    def test_create_search_embed_no_results(self) -> None:
        """Should handle empty results."""
        embed = create_search_embed("no match", [])

        assert embed.description == "No results found."
        assert len(embed.fields) == 0

    def test_create_search_embed_max_results(self) -> None:
        """Should limit to 5 results."""
        results = [
            (f"doc{i}", f"Content {i}", {"source": f"docs/{i}.md"})
            for i in range(10)
        ]
        embed = create_search_embed("query", results)

        assert len(embed.fields) == 5

    def test_create_search_embed_long_content(self) -> None:
        """Should truncate long document content."""
        results = [("doc1", "x" * 500, {"source": "test.md"})]
        embed = create_search_embed("query", results)

        assert len(embed.fields[0].value) < 250
        assert embed.fields[0].value.endswith("...")

    def test_create_search_embed_query_truncation(self) -> None:
        """Should truncate long queries in title."""
        long_query = "x" * 200
        embed = create_search_embed(long_query, [])

        assert len(embed.title) <= 120


class TestCreateHelpEmbed:
    """Tests for help embed creation."""

    def test_create_help_embed_basic(self) -> None:
        """Should create valid help embed."""
        embed = create_help_embed()

        assert embed.title == "RepeatNoMore Help"
        assert embed.color == discord.Color.green()

    def test_create_help_embed_commands(self) -> None:
        """Should include all commands."""
        embed = create_help_embed()

        field_names = [f.name for f in embed.fields]
        assert "/ask <question>" in field_names
        assert "/search <query>" in field_names
        assert "@mention" in field_names

    def test_create_help_embed_footer(self) -> None:
        """Should include footer."""
        embed = create_help_embed()

        assert embed.footer is not None
        assert "RepeatNoMore" in embed.footer.text
