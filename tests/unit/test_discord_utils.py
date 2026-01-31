"""Unit tests for Discord utility functions."""

import pytest

from app.discord.utils import (
    split_message,
    extract_question_from_mention,
    format_code_block,
)


class TestSplitMessage:
    """Tests for message splitting utility."""

    def test_short_message_not_split(self) -> None:
        """Messages under limit should not be split."""
        text = "Short message"
        result = split_message(text, max_length=2000)
        assert result == [text]

    def test_exact_limit_not_split(self) -> None:
        """Messages exactly at limit should not be split."""
        text = "x" * 2000
        result = split_message(text, max_length=2000)
        assert result == [text]

    def test_long_message_split_at_paragraph(self) -> None:
        """Long messages should split at paragraph boundaries."""
        text = "First paragraph.\n\nSecond paragraph." + "x" * 100
        result = split_message(text, max_length=50)
        assert len(result) > 1
        assert result[0] == "First paragraph."

    def test_long_message_split_at_newline(self) -> None:
        """Should split at newline when no paragraph break available."""
        text = "First line\nSecond line" + "x" * 100
        result = split_message(text, max_length=20)
        assert len(result) > 1
        assert result[0] == "First line"

    def test_long_message_split_at_sentence(self) -> None:
        """Should split at sentence boundary when no newline available."""
        text = "First sentence. Second sentence" + "x" * 100
        result = split_message(text, max_length=25)
        assert len(result) > 1
        assert result[0] == "First sentence."

    def test_long_message_split_at_space(self) -> None:
        """Should split at word boundary as last resort."""
        text = "word1 word2 word3 word4 word5"
        result = split_message(text, max_length=12)
        assert len(result) > 1
        # Should not split in the middle of a word
        for chunk in result:
            assert not chunk.startswith("ord")

    def test_code_block_preserved(self) -> None:
        """Code blocks should be properly closed/reopened when split."""
        text = "```python\n" + "x" * 50 + "\n```"
        result = split_message(text, max_length=30)
        assert len(result) > 1
        # First chunk should end with closing code block
        assert result[0].endswith("```")
        # Second chunk should start with opening code block
        assert result[1].startswith("```")

    def test_empty_string(self) -> None:
        """Empty string should return list with empty string."""
        result = split_message("")
        assert result == [""]

    def test_custom_split_delimiters(self) -> None:
        """Should respect custom split delimiters."""
        text = "part1|part2|part3"
        result = split_message(text, max_length=10, split_on=["|"])
        assert len(result) >= 2


class TestExtractQuestionFromMention:
    """Tests for mention parsing utility."""

    def test_extract_simple_mention(self) -> None:
        """Should extract question from simple mention."""
        content = "<@123456789> What is FastAPI?"
        result = extract_question_from_mention(content, 123456789)
        assert result == "What is FastAPI?"

    def test_extract_nickname_mention(self) -> None:
        """Should handle nickname mentions."""
        content = "<@!123456789> How do I test?"
        result = extract_question_from_mention(content, 123456789)
        assert result == "How do I test?"

    def test_extract_multiple_mentions(self) -> None:
        """Should handle multiple mentions of same bot."""
        content = "<@123456789> <@123456789> What?"
        result = extract_question_from_mention(content, 123456789)
        assert result == "What?"

    def test_preserve_other_mentions(self) -> None:
        """Should preserve mentions of other users."""
        content = "<@123456789> Hey <@987654321> how are you?"
        result = extract_question_from_mention(content, 123456789)
        assert "<@987654321>" in result
        assert result == "Hey <@987654321> how are you?"

    def test_clean_extra_whitespace(self) -> None:
        """Should clean up extra whitespace."""
        content = "<@123456789>    What   is   this?   "
        result = extract_question_from_mention(content, 123456789)
        assert result == "What is this?"

    def test_mention_only_returns_empty(self) -> None:
        """Mention-only message should return empty string."""
        content = "<@123456789>"
        result = extract_question_from_mention(content, 123456789)
        assert result == ""

    def test_mention_at_end(self) -> None:
        """Should handle mention at end of message."""
        content = "Hello <@123456789>"
        result = extract_question_from_mention(content, 123456789)
        assert result == "Hello"


class TestFormatCodeBlock:
    """Tests for code block formatting."""

    def test_format_without_language(self) -> None:
        """Should format code block without language."""
        code = "print('hello')"
        result = format_code_block(code)
        assert result == "```\nprint('hello')\n```"

    def test_format_with_language(self) -> None:
        """Should format code block with language."""
        code = "def foo():\n    pass"
        result = format_code_block(code, "python")
        assert result == "```python\ndef foo():\n    pass\n```"

    def test_format_empty_code(self) -> None:
        """Should handle empty code."""
        result = format_code_block("")
        assert result == "```\n\n```"

    def test_format_multiline_code(self) -> None:
        """Should preserve multiline code."""
        code = "line1\nline2\nline3"
        result = format_code_block(code, "text")
        assert "line1\nline2\nline3" in result
