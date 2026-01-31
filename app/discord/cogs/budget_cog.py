"""Discord cog for budget status commands."""

from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from app.services.budget_service import BudgetStatus, get_budget_service
from app.utils.logging import get_logger

logger = get_logger(__name__)


def create_budget_embed(status: BudgetStatus) -> discord.Embed:
    """
    Create a budget status embed with visual indicators.

    Args:
        status: BudgetStatus object with current budget data

    Returns:
        discord.Embed: Formatted embed for Discord
    """
    # Color based on usage percentage
    if status.percentage_used >= 95:
        color = discord.Color.red()
        status_emoji = "\U0001f534"  # Red circle
    elif status.percentage_used >= 80:
        color = discord.Color.orange()
        status_emoji = "\U0001f7e0"  # Orange circle
    elif status.percentage_used >= 50:
        color = discord.Color.yellow()
        status_emoji = "\U0001f7e1"  # Yellow circle
    else:
        color = discord.Color.green()
        status_emoji = "\U0001f7e2"  # Green circle

    embed = discord.Embed(
        title=f"{status_emoji} RepeatNoMore Budget Status",
        color=color,
    )

    # Budget bar visualization
    bar_length = 20
    filled = int(status.percentage_used / 100 * bar_length)
    empty = bar_length - filled
    bar = "\u2588" * filled + "\u2591" * empty

    embed.add_field(
        name="Budget Usage",
        value=f"`{bar}` {status.percentage_used:.1f}%",
        inline=False,
    )

    embed.add_field(
        name="Monthly Budget",
        value=f"${status.total_budget:.2f}",
        inline=True,
    )

    embed.add_field(
        name="Used",
        value=f"${status.used_amount:.4f}",
        inline=True,
    )

    embed.add_field(
        name="Remaining",
        value=f"${status.remaining:.4f}",
        inline=True,
    )

    embed.add_field(
        name="Requests This Month",
        value=str(status.requests_used),
        inline=True,
    )

    embed.add_field(
        name="Service Status",
        value="\U00002705 Active" if status.service_active else "\U0000274c Inactive (Budget Exceeded)",
        inline=True,
    )

    embed.add_field(
        name="Billing Month",
        value=status.current_month,
        inline=True,
    )

    # Parse and format the last_updated timestamp
    try:
        updated_dt = datetime.fromisoformat(status.last_updated.replace("Z", "+00:00"))
        updated_str = updated_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, AttributeError):
        updated_str = status.last_updated[:19] if status.last_updated else "Unknown"

    embed.set_footer(text=f"Last updated: {updated_str}")

    return embed


def create_error_embed(error_message: str) -> discord.Embed:
    """Create an error embed."""
    return discord.Embed(
        title="\U0000274c Error",
        description=f"Failed to retrieve budget status: {error_message}",
        color=discord.Color.red(),
    )


class BudgetCog(commands.Cog):
    """Cog for budget-related commands."""

    def __init__(self, bot: commands.Bot) -> None:
        """
        Initialize the budget cog.

        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.budget_service = get_budget_service()
        logger.info("budget_cog_initialized")

    @app_commands.command(
        name="budget-status",
        description="Check current budget usage and limits",
    )
    async def budget_status(self, interaction: discord.Interaction) -> None:
        """
        Show current budget status.

        Displays a visual representation of budget usage including:
        - Progress bar showing usage percentage
        - Total budget and remaining amount
        - Request count for the current month
        - Service active/inactive status
        """
        logger.info(
            "discord_budget_status_requested",
            user=interaction.user.name,
            guild=interaction.guild.name if interaction.guild else "DM",
        )

        await interaction.response.defer(thinking=True)

        try:
            status = self.budget_service.get_status()
            embed = create_budget_embed(status)
            await interaction.followup.send(embed=embed)

            logger.info(
                "discord_budget_status_sent",
                user=interaction.user.name,
                percentage_used=status.percentage_used,
            )

        except Exception as e:
            logger.error("discord_budget_status_failed", error=str(e))
            error_embed = create_error_embed(str(e))
            await interaction.followup.send(embed=error_embed)


async def setup(bot: commands.Bot) -> None:
    """
    Setup function for loading the cog.

    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(BudgetCog(bot))
    logger.info("budget_cog_loaded")
