"""Utility functions for Discord bot."""

import re


def split_message(
    text: str,
    max_length: int = 2000,
    split_on: list[str] | None = None,
) -> list[str]:
    """
    Split a long message into chunks that fit Discord's limit.

    Preserves code blocks and splits at natural boundaries.

    Args:
        text: Text to split
        max_length: Maximum length per chunk (Discord limit is 2000)
        split_on: Delimiters to split on, in order of preference

    Returns:
        List of text chunks
    """
    if split_on is None:
        split_on = ["\n\n", "\n", ". ", " "]

    if len(text) <= max_length:
        return [text]

    chunks = []
    remaining = text
    # Minimum split index to ensure progress (accounts for code block prefix "```\n")
    min_split = 5

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # Find the best split point
        split_index = None

        for delimiter in split_on:
            # Look for delimiter before max_length
            index = remaining.rfind(delimiter, 0, max_length)
            # Ensure we make enough progress to avoid infinite loops
            if index >= min_split:
                split_index = index + len(delimiter)
                break

        # If no good split point found, hard cut at max_length
        if split_index is None:
            split_index = max_length

        # Check if we're in a code block
        chunk = remaining[:split_index]
        code_blocks_open = chunk.count("```") % 2 == 1

        if code_blocks_open:
            closing_tag = "\n```"
            # Ensure chunk + closing tag fits in max_length
            if len(chunk) + len(closing_tag) > max_length:
                split_index = max(min_split, max_length - len(closing_tag))
                chunk = remaining[:split_index]

            # Close the code block in this chunk and reopen in next
            chunk += closing_tag
            remaining = "```\n" + remaining[split_index:]
        else:
            remaining = remaining[split_index:]

        chunks.append(chunk.strip())

    return chunks


def extract_question_from_mention(content: str, bot_id: int) -> str:
    """
    Extract the question from a message that mentions the bot.

    Args:
        content: Message content
        bot_id: Bot's user ID

    Returns:
        Cleaned question text
    """
    # Remove mentions
    content = re.sub(rf"<@!?{bot_id}>", "", content)
    # Clean up extra whitespace
    content = " ".join(content.split())
    return content.strip()


def format_code_block(code: str, language: str = "") -> str:
    """Format code as a Discord code block."""
    return f"```{language}\n{code}\n```"
