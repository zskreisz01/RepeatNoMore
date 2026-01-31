"""Discord bot implementation for RepeatNoMore."""

import asyncio
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from app.config import get_settings
from app.discord.embeds import (
    create_answer_embed,
    create_error_embed,
    create_help_embed,
    create_search_embed,
)
from app.discord.utils import extract_question_from_mention
from app.events.setup import setup_event_handlers, set_notification_bot
from app.services.qa_service import process_question
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RepeatNoMoreBot(commands.Bot):
    """RepeatNoMore Discord bot with slash commands and mention support."""

    def __init__(self) -> None:
        settings = get_settings()

        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True

        super().__init__(
            command_prefix=settings.discord_command_prefix,
            intents=intents,
            description="RepeatNoMore - AI-powered framework assistant",
        )

        self.settings = settings

    async def setup_hook(self) -> None:
        """Called when bot is starting up."""
        logger.info("discord_bot_setup_started")

        # Load command cogs
        await self.add_cog(QACog(self))

        # Load workflow cog
        from app.discord.cogs.workflow_cog import WorkflowCog
        self.workflow_cog = WorkflowCog(self)
        await self.add_cog(self.workflow_cog)

        # Load budget cog
        from app.discord.cogs.budget_cog import BudgetCog
        await self.add_cog(BudgetCog(self))

        # Sync slash commands
        if self.settings.discord_guild_ids:
            # Sync to specific guilds first (instant) - BEFORE clearing global
            for guild_id in self.settings.discord_guild_ids:
                guild = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info("discord_commands_synced", guild_id=guild_id)

            # Now clear global commands to avoid duplicates
            self.tree.clear_commands(guild=None)
            await self.tree.sync()  # Sync empty global commands
            logger.info("discord_global_commands_cleared")
        else:
            # Global sync (takes up to an hour to propagate)
            await self.tree.sync()
            logger.info("discord_commands_synced_globally")

    async def on_ready(self) -> None:
        """Called when bot is connected and ready."""
        if self.user is None:
            logger.error("discord_bot_user_not_set")
            return

        logger.info(
            "discord_bot_ready",
            username=self.user.name,
            user_id=self.user.id,
            guild_count=len(self.guilds),
        )

        # Log all connected guilds with IDs (helpful for setting DISCORD_GUILD_IDS)
        for guild in self.guilds:
            logger.info(
                "discord_connected_guild",
                guild_name=guild.name,
                guild_id=guild.id,
            )

        # Initialize event handlers with bot reference
        setup_event_handlers(self)
        set_notification_bot(self)
        logger.info("event_system_initialized")

        # Set presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/ask for help",
            )
        )

    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages for mention-based interaction."""
        # Ignore own messages
        if self.user is None or message.author == self.user:
            return

        # Ignore bot messages
        if message.author.bot:
            return

        # Check if bot was mentioned
        if self.user.mentioned_in(message) and self.settings.discord_enable_mentions:
            await self._handle_mention(message)
            return

        # Process prefix commands
        await self.process_commands(message)

    async def _handle_mention(self, message: discord.Message) -> None:
        """Handle when bot is mentioned in a message."""
        if self.user is None:
            return

        question = extract_question_from_mention(message.content, self.user.id)

        if not question:
            await message.reply(
                "Hi! I'm RepeatNoMore. Ask me anything or use `/ask` for the full experience!",
                mention_author=False,
            )
            return

        logger.info(
            "discord_mention_received",
            user=message.author.name,
            guild=message.guild.name if message.guild else "DM",
            question=question[:100],
        )

        # Show typing indicator
        async with message.channel.typing():
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: process_question(question, source="discord_mention"),
                )

                embed = create_answer_embed(question, result)

                # Store Q&A context for accept/reject commands
                if hasattr(self, 'workflow_cog') and self.workflow_cog:
                    self.workflow_cog.store_qa_context(
                        user_id=message.author.id,
                        question=question,
                        answer=result.answer,
                    )

                await message.reply(embed=embed, mention_author=False)

            except Exception as e:
                logger.error("discord_mention_processing_failed", error=str(e))
                embed = create_error_embed(str(e))
                await message.reply(embed=embed, mention_author=False)


class QACog(commands.Cog):
    """Cog containing QA-related commands."""

    def __init__(self, bot: RepeatNoMoreBot) -> None:
        self.bot = bot

    @app_commands.command(name="ask", description="Ask RepeatNoMore a question")
    @app_commands.describe(question="Your question about the framework")
    async def ask(self, interaction: discord.Interaction, question: str) -> None:
        """Slash command to ask a question."""
        logger.info(
            "discord_slash_ask",
            user=interaction.user.name,
            guild=interaction.guild.name if interaction.guild else "DM",
            question=question[:100],
        )

        # Defer the response (allows up to 15 minutes to respond)
        await interaction.response.defer(thinking=True)

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: process_question(question, source="discord_slash"),
            )

            embed = create_answer_embed(question, result)

            # Store Q&A context for accept/reject commands
            if hasattr(self.bot, 'workflow_cog') and self.bot.workflow_cog:
                self.bot.workflow_cog.store_qa_context(
                    user_id=interaction.user.id,
                    question=question,
                    answer=result.answer,
                )

            # Add hint about accept/reject
            embed.set_footer(
                text="Use /accept to save this Q&A to docs, or /reject if the answer is wrong"
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("discord_slash_ask_failed", error=str(e))
            embed = create_error_embed(str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="search", description="Search the knowledge base")
    @app_commands.describe(query="Your search query")
    async def search(self, interaction: discord.Interaction, query: str) -> None:
        """Slash command to search documents."""
        logger.info(
            "discord_slash_search",
            user=interaction.user.name,
            guild=interaction.guild.name if interaction.guild else "DM",
            query=query[:100],
        )

        await interaction.response.defer(thinking=True)

        try:
            from app.rag.vector_store import get_vector_store

            store = get_vector_store()
            results = store.query(query_text=query, n_results=5)

            # Format results for embed
            formatted_results = []
            if results["ids"][0]:
                for doc_id, doc, metadata in zip(
                    results["ids"][0],
                    results["documents"][0],
                    results["metadatas"][0],
                    strict=False,
                ):
                    formatted_results.append((doc_id, doc, metadata))

            embed = create_search_embed(query, formatted_results)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("discord_search_failed", error=str(e))
            embed = create_error_embed(str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="help", description="Show RepeatNoMore help")
    async def help_command(self, interaction: discord.Interaction) -> None:
        """Show help information."""
        embed = create_help_embed()
        await interaction.response.send_message(embed=embed)


async def run_discord_bot() -> None:
    """Run the Discord bot."""
    settings = get_settings()

    if not settings.discord_bot_token:
        logger.error("discord_bot_token_not_configured")
        raise ValueError("DISCORD_BOT_TOKEN must be set")

    bot = RepeatNoMoreBot()

    try:
        logger.info("starting_discord_bot")
        await bot.start(settings.discord_bot_token)
    except KeyboardInterrupt:
        logger.info("discord_bot_shutting_down")
        await bot.close()
