"""Discord embed formatters for RepeatNoMore responses."""

import discord

from app.services.qa_service import QAResult


def create_answer_embed(
    question: str,
    result: QAResult,
    color: discord.Color | None = None,
) -> discord.Embed:
    """
    Create a Discord embed for a QA answer.

    Args:
        question: The original question
        result: QAResult from the QA service
        color: Embed color (defaults to blue)

    Returns:
        discord.Embed: Formatted embed
    """
    if color is None:
        color = discord.Color.blue()

    embed = discord.Embed(title="RepeatNoMore Answer", color=color)

    # Question field
    embed.add_field(
        name="Question",
        value=question[:1024],  # Field value limit
        inline=False,
    )

    # Answer - handle length limits (embed description: 4096, field value: 1024)
    answer = result.answer
    if len(answer) <= 4096:
        embed.description = answer
    else:
        # Truncate and indicate continuation
        embed.description = answer[:4090] + "..."

    # Sources
    if result.sources:
        source_text = "\n".join(
            [f"- {s['metadata'].get('source', 'Unknown')}" for s in result.sources[:5]]
        )
        embed.add_field(
            name="Sources",
            value=source_text[:1024],
            inline=False,
        )

    # Footer with metadata
    if result.confidence >= 0.7:
        confidence_emoji = "\U0001f7e2"  # Green circle
    elif result.confidence >= 0.4:
        confidence_emoji = "\U0001f7e1"  # Yellow circle
    else:
        confidence_emoji = "\U0001f534"  # Red circle

    embed.set_footer(
        text=f"{confidence_emoji} Confidence: {result.confidence:.0%} | "
        f"Time: {result.processing_time:.2f}s | Model: {result.model}"
    )

    return embed


def create_error_embed(
    error_message: str,
    color: discord.Color | None = None,
) -> discord.Embed:
    """Create an error embed."""
    if color is None:
        color = discord.Color.red()

    embed = discord.Embed(
        title="Error",
        description=f"Sorry, I encountered an error:\n```{error_message[:1000]}```",
        color=color,
    )
    embed.set_footer(text="Please try again or contact support if the issue persists.")
    return embed


def create_search_embed(
    query: str,
    results: list[tuple[str, str, dict]],
    color: discord.Color | None = None,
) -> discord.Embed:
    """
    Create a Discord embed for search results.

    Args:
        query: The search query
        results: List of (doc_id, document, metadata) tuples
        color: Embed color (defaults to blue)

    Returns:
        discord.Embed: Formatted embed
    """
    if color is None:
        color = discord.Color.blue()

    embed = discord.Embed(
        title=f"Search Results: {query[:100]}",
        color=color,
    )

    if results:
        for i, (doc_id, doc, metadata) in enumerate(results[:5], 1):
            source = metadata.get("source", "Unknown")
            preview = doc[:200] + "..." if len(doc) > 200 else doc
            embed.add_field(
                name=f"{i}. {source}",
                value=preview,
                inline=False,
            )
    else:
        embed.description = "No results found."

    return embed


def create_help_embed() -> discord.Embed:
    """Create help information embed."""
    embed = discord.Embed(
        title="RepeatNoMore Help",
        description="I'm an AI-powered framework assistant. Here's how to use me:",
        color=discord.Color.green(),
    )

    embed.add_field(
        name="/ask <question>",
        value="Ask me any question about the framework",
        inline=False,
    )
    embed.add_field(
        name="/search <query>",
        value="Search the knowledge base",
        inline=False,
    )
    embed.add_field(
        name="@mention",
        value="Mention me with a question for a quick answer",
        inline=False,
    )

    embed.set_footer(text="Powered by RepeatNoMore RAG")

    return embed
