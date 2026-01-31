"""Discord cog for documentation management workflow commands."""

import asyncio
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from app.services.workflow_service import get_workflow_service
from app.services.permission_service import get_permission_service
from app.services.language_service import get_language_service
from app.agents.draft_agent import get_draft_agent
from app.storage.models import Language
from app.utils.logging import get_logger

logger = get_logger(__name__)


def create_success_embed(title: str, description: str) -> discord.Embed:
    """Create a success embed."""
    return discord.Embed(
        title=title,
        description=description,
        color=discord.Color.green()
    )


def create_error_embed(title: str, description: str) -> discord.Embed:
    """Create an error embed."""
    return discord.Embed(
        title=title,
        description=description,
        color=discord.Color.red()
    )


def create_info_embed(title: str, description: str) -> discord.Embed:
    """Create an info embed."""
    return discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue()
    )


class WorkflowCog(commands.Cog):
    """Cog for documentation management workflow commands."""

    def __init__(self, bot: commands.Bot):
        """Initialize the workflow cog."""
        self.bot = bot
        self.workflow_service = get_workflow_service()
        self.permission_service = get_permission_service()
        self.language_service = get_language_service()
        self.draft_agent = get_draft_agent()
        # Store last Q&A context per user for accept/reject
        self._user_qa_context: dict[int, dict] = {}
        logger.info("workflow_cog_initialized")

    def _get_user_email(self, user: discord.User | discord.Member) -> str:
        """
        Get user email from Discord user.

        In production, this could integrate with a user database.
        For now, use Discord ID + name as identifier.
        """
        # Check if user has linked email (would require OAuth or database)
        # For now, use a constructed identifier
        return f"{user.name}@discord.user"

    def _is_admin(self, user: discord.User | discord.Member) -> bool:
        """Check if Discord user is an admin."""
        user_email = self._get_user_email(user)
        return self.permission_service.is_admin(user_email)

    def store_qa_context(
        self,
        user_id: int,
        question: str,
        answer: str,
        language: str = "en"
    ) -> None:
        """Store Q&A context for a user (for accept/reject)."""
        self._user_qa_context[user_id] = {
            "question": question,
            "answer": answer,
            "language": language
        }

    # ==================== Q&A Workflow Commands ====================

    @app_commands.command(
        name="accept",
        description="Accept the last Q&A answer and save it to documentation"
    )
    async def accept_answer(self, interaction: discord.Interaction) -> None:
        """Accept the last Q&A and save to documentation."""
        await interaction.response.defer(thinking=True)

        user_id = interaction.user.id
        context = self._user_qa_context.get(user_id)

        if not context:
            embed = create_error_embed(
                "No Q&A Context",
                "No recent Q&A to accept. Ask a question first using `/ask`."
            )
            await interaction.followup.send(embed=embed)
            return

        try:
            user_email = self._get_user_email(interaction.user)
            result = await self.workflow_service.accept_qa(
                question=context["question"],
                answer=context["answer"],
                user_email=user_email,
                language=context.get("language", "en"),
            )

            if result.get("success"):
                embed = create_success_embed(
                    "Q&A Accepted",
                    f"Your Q&A has been saved to the documentation.\n\n"
                    f"**ID:** {result.get('qa_id')}"
                )
                # Clear context after acceptance
                del self._user_qa_context[user_id]
            else:
                embed = create_error_embed(
                    "Failed to Save",
                    result.get("error", "Unknown error occurred")
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("accept_command_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="reject",
        description="Reject the last answer and escalate to admins"
    )
    @app_commands.describe(reason="Reason for rejection (optional)")
    async def reject_answer(
        self,
        interaction: discord.Interaction,
        reason: Optional[str] = None
    ) -> None:
        """Reject the last answer and escalate to admin queue."""
        await interaction.response.defer(thinking=True)

        user_id = interaction.user.id
        context = self._user_qa_context.get(user_id)

        if not context:
            embed = create_error_embed(
                "No Q&A Context",
                "No recent Q&A to reject. Ask a question first using `/ask`."
            )
            await interaction.followup.send(embed=embed)
            return

        try:
            user_email = self._get_user_email(interaction.user)
            result = await self.workflow_service.escalate_question(
                question=context["question"],
                bot_answer=context["answer"],
                user_email=user_email,
                rejection_reason=reason,
                platform="discord",
                conversation_id=str(interaction.channel_id),
                language=context.get("language", "en"),
            )

            embed = create_info_embed(
                "Question Escalated",
                f"Your question has been escalated to the admin queue.\n\n"
                f"**Question ID:** {result.get('question_id')}\n"
                f"An administrator will review it shortly."
            )
            # Clear context after rejection
            del self._user_qa_context[user_id]

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("reject_command_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    # ==================== Accepted Q&A Commands ====================

    @app_commands.command(
        name="get-qa",
        description="View details of an accepted Q&A by ID"
    )
    @app_commands.describe(qa_id="Q&A ID (e.g., QA-5D18ECF2)")
    async def get_qa(
        self,
        interaction: discord.Interaction,
        qa_id: str
    ) -> None:
        """View details of an accepted Q&A."""
        await interaction.response.defer(thinking=True)

        try:
            user_email = self._get_user_email(interaction.user)
            user_lang = self.language_service.get_user_preference(user_email)

            qa = self.workflow_service.get_accepted_qa(qa_id, user_lang.value)

            if not qa:
                embed = create_error_embed(
                    "Q&A Not Found",
                    f"No accepted Q&A found with ID: {qa_id}\n\n"
                    f"Use `/list-qa` to see recent accepted Q&A pairs.\n"
                    f"Note: Older Q&A entries may not have IDs stored."
                )
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title=f"Accepted Q&A: {qa['id']}",
                color=discord.Color.green()
            )
            embed.add_field(name="Language", value=qa["language"].upper(), inline=True)
            embed.add_field(name="Accepted On", value=qa["accepted_on"], inline=True)

            # Question (truncate if too long)
            question = qa["question"]
            if len(question) > 1000:
                question = question[:997] + "..."
            embed.add_field(name="Question", value=question, inline=False)

            # Answer (truncate if too long for embed)
            answer = qa["answer"]
            if len(answer) > 1000:
                answer = answer[:997] + "..."
            embed.add_field(name="Answer", value=answer, inline=False)

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("get_qa_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="list-qa",
        description="List recent accepted Q&A pairs"
    )
    @app_commands.describe(limit="Number of Q&A pairs to show (default: 10)")
    async def list_qa(
        self,
        interaction: discord.Interaction,
        limit: int = 10
    ) -> None:
        """List recent accepted Q&A pairs."""
        await interaction.response.defer(thinking=True)

        try:
            user_email = self._get_user_email(interaction.user)
            user_lang = self.language_service.get_user_preference(user_email)

            qa_list = self.workflow_service.list_accepted_qa(user_lang.value, min(limit, 25))

            if not qa_list:
                embed = create_info_embed(
                    "No Accepted Q&A",
                    f"No accepted Q&A pairs found for language: {user_lang.value.upper()}\n\n"
                    f"Use `/accept` after asking a question to save Q&A to documentation."
                )
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title=f"Accepted Q&A ({user_lang.value.upper()})",
                description=f"Showing {len(qa_list)} most recent accepted Q&A pairs",
                color=discord.Color.blue()
            )

            for qa in qa_list:
                embed.add_field(
                    name=f"{qa['id']} ({qa['accepted_on']})",
                    value=qa["question"],
                    inline=False
                )

            embed.set_footer(text="Use /get-qa <id> to view full details")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("list_qa_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    # ==================== Feature Suggestion ====================

    @app_commands.command(
        name="suggest-feature",
        description="Suggest a new feature for the framework or documentation"
    )
    @app_commands.describe(
        title="Feature title",
        description="Detailed description of the feature"
    )
    async def suggest_feature(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str
    ) -> None:
        """Submit a feature suggestion."""
        await interaction.response.defer(thinking=True)

        try:
            user_email = self._get_user_email(interaction.user)
            user_lang = self.language_service.get_user_preference(user_email)

            result = await self.workflow_service.suggest_feature(
                title=title,
                description=description,
                user_email=user_email,
                language=user_lang.value,
            )

            if result.get("success"):
                embed = create_success_embed(
                    "Feature Suggested",
                    f"Your feature suggestion has been recorded.\n\n"
                    f"**Feature ID:** {result.get('feature_id')}\n"
                    f"**Title:** {title}"
                )
            else:
                embed = create_error_embed(
                    "Failed to Submit",
                    result.get("error", "Unknown error occurred")
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("suggest_feature_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    # ==================== Draft Suggestion ====================

    @app_commands.command(
        name="suggest-docs-change",
        description="Suggest a documentation change (AI will analyze and create draft)"
    )
    @app_commands.describe(
        suggestion="Describe what documentation change you want to make",
        context="Optional: specific topic or file to focus on"
    )
    async def suggest_docs_change(
        self,
        interaction: discord.Interaction,
        suggestion: str,
        context: Optional[str] = None
    ) -> None:
        """
        Suggest a documentation change using AI analysis.

        The AI agent will:
        1. Analyze your suggestion
        2. Find the relevant documentation file
        3. Determine where to make changes
        4. Generate the actual content
        5. Create a draft for admin review
        """
        await interaction.response.defer(thinking=True)

        try:
            user_email = self._get_user_email(interaction.user)
            user_lang = self.language_service.get_user_preference(user_email)

            # Show initial status
            status_embed = create_info_embed(
                "Analyzing Suggestion...",
                "The AI is analyzing your suggestion and finding relevant documentation."
            )
            await interaction.followup.send(embed=status_embed)

            # Use draft agent to analyze the suggestion
            draft_agent = get_draft_agent()
            analysis_result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: draft_agent.analyze_suggestion(
                    suggestion=suggestion,
                    context_query=context
                )
            )

            if not analysis_result.get("success"):
                embed = create_error_embed(
                    "Analysis Failed",
                    analysis_result.get("error", "Failed to analyze suggestion")
                )
                await interaction.followup.send(embed=embed)
                return

            draft_suggestion = analysis_result["draft"]

            # Create the actual draft in the workflow system
            result = await self.workflow_service.create_draft_update(
                content=draft_suggestion.suggested_content,
                target_section=f"{draft_suggestion.target_file}#{draft_suggestion.target_section}",
                user_email=user_email,
                description=f"[AI-Analyzed] {draft_suggestion.rationale}",
                language=user_lang.value,
            )

            if result.get("success"):
                # Create detailed response embed
                embed = create_success_embed(
                    "Draft Created from Suggestion",
                    f"AI has analyzed your suggestion and created a draft."
                )
                embed.add_field(
                    name="Draft ID",
                    value=result.get("draft_id"),
                    inline=True
                )
                embed.add_field(
                    name="Target File",
                    value=draft_suggestion.target_file,
                    inline=True
                )
                embed.add_field(
                    name="Target Section",
                    value=draft_suggestion.target_section,
                    inline=True
                )
                embed.add_field(
                    name="Change Type",
                    value=draft_suggestion.change_type.capitalize(),
                    inline=True
                )
                embed.add_field(
                    name="AI Confidence",
                    value=f"{draft_suggestion.confidence * 100:.0f}%",
                    inline=True
                )

                if draft_suggestion.requires_mkdocs_update:
                    embed.add_field(
                        name="MkDocs Update",
                        value=draft_suggestion.mkdocs_changes or "Navigation update needed",
                        inline=False
                    )

                # Show content preview
                content_preview = draft_suggestion.suggested_content[:500]
                if len(draft_suggestion.suggested_content) > 500:
                    content_preview += "..."
                embed.add_field(
                    name="Content Preview",
                    value=f"```md\n{content_preview}\n```",
                    inline=False
                )

                embed.add_field(
                    name="AI Rationale",
                    value=draft_suggestion.rationale[:300],
                    inline=False
                )

                embed.set_footer(
                    text="Use /get-draft to see full content | An admin will review this draft"
                )
            else:
                embed = create_error_embed(
                    "Failed to Create Draft",
                    result.get("error", "Unknown error occurred")
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("suggest_docs_change_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="create-draft",
        description="Create a draft documentation update (manual mode)"
    )
    @app_commands.describe(
        target_file="Target file path (e.g., docs/getting_started.md)",
        target_section="Target section heading",
        content="The draft content/update",
        description="Description of the change"
    )
    async def create_draft(
        self,
        interaction: discord.Interaction,
        target_file: str,
        target_section: str,
        content: str,
        description: Optional[str] = None
    ) -> None:
        """Create a draft documentation update manually (without AI analysis)."""
        await interaction.response.defer(thinking=True)

        try:
            user_email = self._get_user_email(interaction.user)
            user_lang = self.language_service.get_user_preference(user_email)

            result = await self.workflow_service.create_draft_update(
                content=content,
                target_section=f"{target_file}#{target_section}",
                user_email=user_email,
                description=description,
                language=user_lang.value,
            )

            if result.get("success"):
                embed = create_success_embed(
                    "Draft Created",
                    f"Your draft update has been submitted for review.\n\n"
                    f"**Draft ID:** {result.get('draft_id')}\n"
                    f"**Target:** {target_file}#{target_section}\n\n"
                    f"An administrator will review your submission."
                )
            else:
                embed = create_error_embed(
                    "Failed to Create Draft",
                    result.get("error", "Unknown error occurred")
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("create_draft_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    # ==================== Admin Commands ====================

    @app_commands.command(
        name="edit-docs",
        description="[Admin] Edit documentation with natural language instruction"
    )
    @app_commands.describe(
        instruction="Natural language instruction for editing",
        target_file="Target file to edit (optional)"
    )
    async def edit_docs(
        self,
        interaction: discord.Interaction,
        instruction: str,
        target_file: Optional[str] = None
    ) -> None:
        """Edit documentation (admin only)."""
        await interaction.response.defer(thinking=True)

        user_email = self._get_user_email(interaction.user)

        if not self.permission_service.is_admin(user_email):
            embed = create_error_embed(
                "Permission Denied",
                "Only administrators can edit documentation directly."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            user_lang = self.language_service.get_user_preference(user_email)

            result = await self.workflow_service.edit_docs(
                instruction=instruction,
                admin_email=user_email,
                target_file=target_file,
                language=user_lang.value,
            )

            embed = create_info_embed(
                "Edit Request Received",
                f"{result.get('message', 'Documentation edit request processed.')}\n\n"
                f"**Instruction:** {instruction[:200]}..."
            )

            await interaction.followup.send(embed=embed)

        except PermissionError as e:
            embed = create_error_embed("Permission Denied", str(e))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error("edit_docs_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="accept-draft",
        description="[Admin] Accept and apply a draft update"
    )
    @app_commands.describe(draft_id="Draft ID (e.g., DRAFT-A9F4BE76 or A9F4BE76)")
    async def accept_draft(
        self,
        interaction: discord.Interaction,
        draft_id: str
    ) -> None:
        """Accept and apply a draft update (admin only)."""
        await interaction.response.defer(thinking=True)

        user_email = self._get_user_email(interaction.user)

        if not self.permission_service.is_admin(user_email):
            embed = create_error_embed(
                "Permission Denied",
                "Only administrators can accept drafts."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            # Normalize draft ID
            normalized_id = draft_id.upper()
            if not normalized_id.startswith("DRAFT-"):
                normalized_id = f"DRAFT-{normalized_id}"

            result = await self.workflow_service.accept_draft(
                draft_id=normalized_id,
                admin_email=user_email,
                apply_immediately=True,
            )

            if result.get("success"):
                embed = create_success_embed(
                    "Draft Accepted",
                    f"Draft **{normalized_id}** has been accepted and applied.\n\n"
                    f"**Approved by:** {user_email}"
                )
                if result.get("pr_url"):
                    embed.add_field(
                        name="Pull Request",
                        value=result["pr_url"],
                        inline=False
                    )
            else:
                embed = create_error_embed(
                    "Failed to Accept Draft",
                    result.get("error", "Unknown error occurred")
                )

            await interaction.followup.send(embed=embed)

        except PermissionError as e:
            embed = create_error_embed("Permission Denied", str(e))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except ValueError as e:
            embed = create_error_embed("Draft Not Found", str(e))
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error("accept_draft_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="list-drafts",
        description="List all draft updates with metadata"
    )
    async def list_drafts(self, interaction: discord.Interaction) -> None:
        """List all draft updates with metadata and topic."""
        await interaction.response.defer(thinking=True)

        try:
            # Get all drafts, not just pending
            drafts = self.workflow_service.draft_repo.get_all()

            if not drafts:
                embed = create_info_embed(
                    "No Drafts",
                    "There are no draft updates in the system.\n\n"
                    "Use `/suggest-docs-change` or `/create-draft` to create one."
                )
            else:
                embed = create_info_embed(
                    f"All Drafts ({len(drafts)})",
                    "Documentation draft updates:"
                )
                for draft in drafts[:10]:  # Limit to 10
                    status_indicator = {
                        "pending": "Pending",
                        "approved": "Approved",
                        "rejected": "Rejected",
                        "applied": "Applied"
                    }.get(draft.status, draft.status)

                    embed.add_field(
                        name=f"{draft.id}",
                        value=f"**Topic:** {draft.target_section}\n"
                              f"**Status:** {status_indicator}\n"
                              f"**By:** {draft.user_email}\n"
                              f"**Date:** {draft.created_at[:10]}",
                        inline=True
                    )
                if len(drafts) > 10:
                    embed.set_footer(text=f"Showing 10 of {len(drafts)} drafts. Use /get-draft <id> for details.")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("list_drafts_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="list-pending-drafts",
        description="List only pending draft updates awaiting review"
    )
    async def list_pending_drafts(self, interaction: discord.Interaction) -> None:
        """List only pending draft updates."""
        await interaction.response.defer(thinking=True)

        try:
            # Get all drafts and filter for pending only
            all_drafts = self.workflow_service.draft_repo.get_all()
            pending_drafts = [d for d in all_drafts if d.status == "pending"]

            if not pending_drafts:
                embed = create_info_embed(
                    "No Pending Drafts",
                    "There are no pending draft updates awaiting review.\n\n"
                    "Use `/suggest-docs-change` or `/create-draft` to create one."
                )
            else:
                embed = create_info_embed(
                    f"Pending Drafts ({len(pending_drafts)})",
                    "Draft updates awaiting review:"
                )
                for draft in pending_drafts[:15]:  # Limit to 15
                    embed.add_field(
                        name=f"{draft.id}",
                        value=f"**Topic:** {draft.target_section}\n"
                              f"**By:** {draft.user_email}\n"
                              f"**Date:** {draft.created_at[:10]}",
                        inline=True
                    )
                if len(pending_drafts) > 15:
                    embed.set_footer(text=f"Showing 15 of {len(pending_drafts)} pending drafts.")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("list_pending_drafts_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="get-draft",
        description="View details of a specific draft"
    )
    @app_commands.describe(draft_id="Draft ID (e.g., DRAFT-A9F4BE76 or A9F4BE76)")
    async def get_draft(
        self,
        interaction: discord.Interaction,
        draft_id: str
    ) -> None:
        """View details of a specific draft."""
        await interaction.response.defer(thinking=True)

        try:
            # Normalize draft ID - add DRAFT- prefix if not present
            normalized_id = draft_id.upper()
            if not normalized_id.startswith("DRAFT-"):
                normalized_id = f"DRAFT-{normalized_id}"

            draft = self.workflow_service.draft_repo.get(normalized_id)

            if not draft:
                embed = create_error_embed(
                    "Draft Not Found",
                    f"No draft found with ID: {draft_id}\n\n"
                    f"Use `/list-drafts` to see available drafts."
                )
                await interaction.followup.send(embed=embed)
                return

            # Determine color based on status
            status_colors = {
                "pending": discord.Color.yellow(),
                "approved": discord.Color.green(),
                "rejected": discord.Color.red(),
                "applied": discord.Color.blue()
            }
            color = status_colors.get(draft.status, discord.Color.default())

            # Parse target_section to extract file and section
            target_file = "Unknown"
            target_section = draft.target_section
            if "#" in draft.target_section:
                parts = draft.target_section.split("#", 1)
                target_file = parts[0]
                target_section = parts[1] if len(parts) > 1 else "Unknown"

            embed = discord.Embed(
                title=f"Draft: {draft.id}",
                description=draft.description or "No description provided.",
                color=color
            )
            embed.add_field(name="Target File", value=f"`{target_file}`", inline=True)
            embed.add_field(name="Target Section", value=target_section, inline=True)
            embed.add_field(name="Change Type", value="Add/Modify", inline=True)
            embed.add_field(name="Status", value=draft.status.upper(), inline=True)
            embed.add_field(name="Language", value=draft.language.upper(), inline=True)
            embed.add_field(name="Submitted By", value=draft.user_email, inline=True)
            embed.add_field(name="Created", value=draft.created_at[:10], inline=True)

            if draft.approved_by:
                embed.add_field(name="Approved By", value=draft.approved_by, inline=True)
            if draft.rejection_reason:
                embed.add_field(name="Rejection Reason", value=draft.rejection_reason, inline=False)

            await interaction.followup.send(embed=embed)

            # Send the full content as a separate message with Discord-compatible formatting
            # Discord doesn't support markdown headers (##) so convert to bold
            def format_for_discord(text: str) -> str:
                """Convert markdown to Discord-compatible format."""
                import re
                # Convert literal \n to actual newlines
                text = text.replace("\\n", "\n")
                # Convert markdown headers to bold text
                # ### Header -> **Header**
                text = re.sub(r'^###\s+(.+)$', r'**\1**', text, flags=re.MULTILINE)
                # ## Header -> **Header**
                text = re.sub(r'^##\s+(.+)$', r'**\1**', text, flags=re.MULTILINE)
                # # Header -> **Header**
                text = re.sub(r'^#\s+(.+)$', r'**\1**', text, flags=re.MULTILINE)
                # Convert --- to a visual separator (Discord doesn't render hr)
                text = re.sub(r'^---+$', r'━━━━━━━━━━━━━━━━━━━━', text, flags=re.MULTILINE)
                return text

            content_header = f"**Suggested Content for** `{target_file}`\n"
            content_header += f"**Section:** {target_section}\n"
            content_header += "━━━━━━━━━━━━━━━━━━━━\n\n"

            formatted_content = format_for_discord(draft.content)
            full_content = content_header + formatted_content

            # Discord message limit is 2000 chars, split if needed
            if len(full_content) <= 1900:
                await interaction.followup.send(full_content)
            else:
                # Send header first
                await interaction.followup.send(content_header)
                # Split content into chunks of ~1800 chars at newline boundaries
                content = formatted_content
                chunks = []
                current_chunk = ""
                for line in content.split("\n"):
                    if len(current_chunk) + len(line) + 1 > 1800:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = line
                    else:
                        current_chunk = current_chunk + "\n" + line if current_chunk else line
                if current_chunk:
                    chunks.append(current_chunk)

                for i, chunk in enumerate(chunks):
                    prefix = "" if i == 0 else "*(continued)*\n"
                    await interaction.followup.send(f"{prefix}{chunk}")

        except Exception as e:
            logger.error("get_draft_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="change-draft",
        description="[Admin] Modify a draft using AI (describe what to change)"
    )
    @app_commands.describe(
        draft_id="Draft ID (e.g., DRAFT-A9F4BE76 or A9F4BE76)",
        instruction="Describe how to modify the draft (e.g., 'add more details about authentication')"
    )
    async def change_draft(
        self,
        interaction: discord.Interaction,
        draft_id: str,
        instruction: str
    ) -> None:
        """Modify a draft's content using AI based on instruction (admin only)."""
        await interaction.response.defer(thinking=True)

        user_email = self._get_user_email(interaction.user)

        if not self.permission_service.is_admin(user_email):
            embed = create_error_embed(
                "Permission Denied",
                "Only administrators can modify drafts."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            # Normalize draft ID
            normalized_id = draft_id.upper()
            if not normalized_id.startswith("DRAFT-"):
                normalized_id = f"DRAFT-{normalized_id}"

            draft = self.workflow_service.draft_repo.get(normalized_id)

            if not draft:
                embed = create_error_embed(
                    "Draft Not Found",
                    f"No draft found with ID: {draft_id}"
                )
                await interaction.followup.send(embed=embed)
                return

            # Show processing status
            status_embed = create_info_embed(
                "Processing Edit...",
                f"AI is modifying draft **{normalized_id}** based on your instruction:\n\n"
                f"*\"{instruction}\"*"
            )
            await interaction.followup.send(embed=status_embed)

            # Parse target info from target_section
            target_file = ""
            target_section = draft.target_section
            if "#" in draft.target_section:
                parts = draft.target_section.split("#", 1)
                target_file = parts[0]
                target_section = parts[1] if len(parts) > 1 else ""

            # Use draft agent to edit the content
            result = self.draft_agent.edit_content(
                current_content=draft.content,
                edit_instruction=instruction,
                target_file=target_file,
                target_section=target_section
            )

            if not result.get("success"):
                embed = create_error_embed(
                    "Edit Failed",
                    f"Failed to apply edit: {result.get('error', 'Unknown error')}"
                )
                await interaction.followup.send(embed=embed)
                return

            # Update the draft with new content
            original_content = draft.content
            draft.content = result["content"]
            updated = self.workflow_service.draft_repo.update(draft)

            if updated:
                changes_summary = result.get("changes_summary", "Content modified")
                embed = create_success_embed(
                    "Draft Updated",
                    f"Draft **{normalized_id}** has been modified by AI.\n\n"
                    f"**Changes:** {changes_summary}\n"
                    f"**Modified by:** {user_email}"
                )
                embed.add_field(
                    name="Instruction",
                    value=instruction[:200] + ("..." if len(instruction) > 200 else ""),
                    inline=False
                )
            else:
                embed = create_error_embed(
                    "Update Failed",
                    "AI generated new content but failed to save the draft."
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("change_draft_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="change-draft-manual",
        description="[Admin] Directly replace a draft's content"
    )
    @app_commands.describe(
        draft_id="Draft ID (e.g., DRAFT-A9F4BE76 or A9F4BE76)",
        new_content="New content to replace the existing draft content"
    )
    async def change_draft_manual(
        self,
        interaction: discord.Interaction,
        draft_id: str,
        new_content: str
    ) -> None:
        """Directly replace a draft's content (admin only)."""
        await interaction.response.defer(thinking=True)

        user_email = self._get_user_email(interaction.user)

        if not self.permission_service.is_admin(user_email):
            embed = create_error_embed(
                "Permission Denied",
                "Only administrators can modify drafts."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            # Normalize draft ID
            normalized_id = draft_id.upper()
            if not normalized_id.startswith("DRAFT-"):
                normalized_id = f"DRAFT-{normalized_id}"

            draft = self.workflow_service.draft_repo.get(normalized_id)

            if not draft:
                embed = create_error_embed(
                    "Draft Not Found",
                    f"No draft found with ID: {draft_id}"
                )
                await interaction.followup.send(embed=embed)
                return

            # Update the draft content directly
            draft.content = new_content
            updated = self.workflow_service.draft_repo.update(draft)

            if updated:
                embed = create_success_embed(
                    "Draft Updated",
                    f"Draft **{normalized_id}** content has been replaced.\n\n"
                    f"**Modified by:** {user_email}"
                )
            else:
                embed = create_error_embed(
                    "Update Failed",
                    "Failed to update the draft."
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("change_draft_manual_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="reject-draft",
        description="[Admin] Reject a draft update with a reason"
    )
    @app_commands.describe(
        draft_id="Draft ID (e.g., DRAFT-A9F4BE76 or A9F4BE76)",
        reason="Reason for rejection"
    )
    async def reject_draft(
        self,
        interaction: discord.Interaction,
        draft_id: str,
        reason: str
    ) -> None:
        """Reject a draft update (admin only)."""
        await interaction.response.defer(thinking=True)

        user_email = self._get_user_email(interaction.user)

        if not self.permission_service.is_admin(user_email):
            embed = create_error_embed(
                "Permission Denied",
                "Only administrators can reject drafts."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            # Normalize draft ID
            normalized_id = draft_id.upper()
            if not normalized_id.startswith("DRAFT-"):
                normalized_id = f"DRAFT-{normalized_id}"

            result = await self.workflow_service.reject_draft(
                draft_id=normalized_id,
                admin_email=user_email,
                reason=reason,
            )

            if result.get("success"):
                embed = create_success_embed(
                    "Draft Rejected",
                    f"Draft **{normalized_id}** has been rejected.\n\n"
                    f"**Reason:** {reason}\n"
                    f"**Rejected by:** {user_email}"
                )
            else:
                embed = create_error_embed(
                    "Failed to Reject Draft",
                    result.get("error", "Unknown error occurred")
                )

            await interaction.followup.send(embed=embed)

        except PermissionError as e:
            embed = create_error_embed("Permission Denied", str(e))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error("reject_draft_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="list-questions",
        description="List all questions in the queue"
    )
    async def list_questions(self, interaction: discord.Interaction) -> None:
        """List all questions in the queue with metadata."""
        await interaction.response.defer(thinking=True)

        try:
            # Get all questions from queue
            questions = self.workflow_service.queue_repo.get_all()

            if not questions:
                embed = create_info_embed(
                    "No Questions",
                    "There are no questions in the queue.\n\n"
                    "Questions appear here when users reject bot answers using `/reject`."
                )
            else:
                embed = create_info_embed(
                    f"Questions Queue ({len(questions)})",
                    "Escalated questions:"
                )
                for q in questions[:10]:  # Limit to 10
                    status_indicator = {
                        "pending": "Pending",
                        "answered": "Answered",
                        "on_hold": "On Hold"
                    }.get(q.status, q.status)

                    question_preview = q.question[:80]
                    if len(q.question) > 80:
                        question_preview += "..."

                    embed.add_field(
                        name=f"{q.id}",
                        value=f"**Question:** {question_preview}\n"
                              f"**Status:** {status_indicator}\n"
                              f"**By:** {q.user_email}\n"
                              f"**Date:** {q.created_at[:10]}",
                        inline=False
                    )
                if len(questions) > 10:
                    embed.set_footer(text=f"Showing 10 of {len(questions)} questions. Use /get-question <id> for details.")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("list_questions_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="get-question",
        description="View details of a specific question"
    )
    @app_commands.describe(question_id="Question ID (e.g., Q-A9F4BE76 or A9F4BE76)")
    async def get_question(
        self,
        interaction: discord.Interaction,
        question_id: str
    ) -> None:
        """View details of a specific question."""
        await interaction.response.defer(thinking=True)

        try:
            # Normalize question ID - add Q- prefix if not present
            normalized_id = question_id.upper()
            if not normalized_id.startswith("Q-"):
                normalized_id = f"Q-{normalized_id}"

            question = self.workflow_service.queue_repo.get(normalized_id)

            if not question:
                embed = create_error_embed(
                    "Question Not Found",
                    f"No question found with ID: {question_id}\n\n"
                    f"Use `/list-questions` to see available questions."
                )
                await interaction.followup.send(embed=embed)
                return

            # Determine color based on status
            status_colors = {
                "pending": discord.Color.yellow(),
                "answered": discord.Color.green(),
                "on_hold": discord.Color.orange()
            }
            color = status_colors.get(question.status, discord.Color.default())

            embed = discord.Embed(
                title=f"Question: {question.id}",
                color=color
            )
            embed.add_field(name="Status", value=question.status.upper(), inline=True)
            embed.add_field(name="Platform", value=question.platform.capitalize(), inline=True)
            embed.add_field(name="Date", value=question.created_at[:10], inline=True)
            embed.add_field(name="Asked By", value=question.user_email, inline=True)

            # Question content
            embed.add_field(
                name="Question",
                value=question.question[:1000],
                inline=False
            )

            # Bot's original answer
            if question.bot_answer:
                bot_answer = question.bot_answer[:800]
                if len(question.bot_answer) > 800:
                    bot_answer += "..."
                embed.add_field(
                    name="Bot's Answer (Rejected)",
                    value=bot_answer,
                    inline=False
                )

            # Rejection reason
            if question.rejection_reason:
                embed.add_field(
                    name="Rejection Reason",
                    value=question.rejection_reason,
                    inline=False
                )

            # Admin response if available
            if question.admin_response:
                embed.add_field(
                    name="Admin Response",
                    value=question.admin_response[:1000],
                    inline=False
                )
                if question.responded_by:
                    embed.add_field(
                        name="Responded By",
                        value=question.responded_by,
                        inline=True
                    )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("get_question_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="answer-question",
        description="[Admin] Answer a question and notify the user"
    )
    @app_commands.describe(
        question_id="Question ID (e.g., Q-A9F4BE76 or A9F4BE76)",
        answer="Your answer to the question"
    )
    async def answer_question(
        self,
        interaction: discord.Interaction,
        question_id: str,
        answer: str
    ) -> None:
        """Answer a question and notify the user (admin only)."""
        await interaction.response.defer(thinking=True)

        user_email = self._get_user_email(interaction.user)

        if not self.permission_service.is_admin(user_email):
            embed = create_error_embed(
                "Permission Denied",
                "Only administrators can answer questions."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            # Normalize question ID
            normalized_id = question_id.upper()
            if not normalized_id.startswith("Q-"):
                normalized_id = f"Q-{normalized_id}"

            # Get the question first
            question = self.workflow_service.queue_repo.get(normalized_id)
            if not question:
                embed = create_error_embed(
                    "Question Not Found",
                    f"No question found with ID: {question_id}"
                )
                await interaction.followup.send(embed=embed)
                return

            # Respond to the question
            result = await self.workflow_service.respond_to_question(
                question_id=normalized_id,
                admin_email=user_email,
                response=answer,
                action="answer",
            )

            if result.get("success"):
                embed = create_success_embed(
                    "Question Answered",
                    f"Your answer to **{normalized_id}** has been recorded.\n\n"
                    f"The user will be notified."
                )

                # Try to notify the user via DM
                original_user_name = question.user_email.replace("@discord.user", "")
                notified = False

                for guild in self.bot.guilds:
                    for member in guild.members:
                        if member.name == original_user_name:
                            try:
                                notify_embed = discord.Embed(
                                    title="Your Question Has Been Answered!",
                                    description="An administrator has answered your escalated question.",
                                    color=discord.Color.green()
                                )
                                notify_embed.add_field(name="Question ID", value=normalized_id, inline=True)
                                notify_embed.add_field(
                                    name="Your Question",
                                    value=question.question[:500],
                                    inline=False
                                )
                                notify_embed.add_field(
                                    name="Answer",
                                    value=answer[:1000],
                                    inline=False
                                )
                                await member.send(embed=notify_embed)
                                notified = True
                                embed.add_field(
                                    name="User Notification",
                                    value=f"DM sent to {original_user_name}",
                                    inline=False
                                )
                            except discord.Forbidden:
                                embed.add_field(
                                    name="User Notification",
                                    value=f"Could not DM {original_user_name} (DMs disabled)",
                                    inline=False
                                )
                            break
                    if notified:
                        break

                if not notified and "User Notification" not in [f.name for f in embed.fields]:
                    embed.add_field(
                        name="User Notification",
                        value=f"Could not find user {original_user_name}",
                        inline=False
                    )
            else:
                embed = create_error_embed(
                    "Failed to Answer",
                    result.get("error", "Unknown error occurred")
                )

            await interaction.followup.send(embed=embed)

        except PermissionError as e:
            embed = create_error_embed("Permission Denied", str(e))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error("answer_question_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="respond",
        description="[Admin] Respond to a pending question"
    )
    @app_commands.describe(
        question_id="The question ID (e.g., Q-ABC12345)",
        response="Your response to the question"
    )
    async def respond_to_question(
        self,
        interaction: discord.Interaction,
        question_id: str,
        response: str
    ) -> None:
        """Respond to a pending question (admin only)."""
        await interaction.response.defer(thinking=True)

        user_email = self._get_user_email(interaction.user)

        if not self.permission_service.is_admin(user_email):
            embed = create_error_embed(
                "Permission Denied",
                "Only administrators can respond to questions."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            result = await self.workflow_service.respond_to_question(
                question_id=question_id,
                admin_email=user_email,
                response=response,
                action="answer",
            )

            if result.get("success"):
                embed = create_success_embed(
                    "Response Recorded",
                    f"Your response to **{question_id}** has been recorded."
                )
            else:
                embed = create_error_embed(
                    "Failed to Respond",
                    result.get("error", "Question not found")
                )

            await interaction.followup.send(embed=embed)

        except PermissionError as e:
            embed = create_error_embed("Permission Denied", str(e))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error("respond_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="git-sync",
        description="[Admin] Sync documentation changes to git repository"
    )
    @app_commands.describe(
        commit_message="Custom commit message (optional)",
        create_pr="Create a pull request"
    )
    async def git_sync(
        self,
        interaction: discord.Interaction,
        commit_message: Optional[str] = None,
        create_pr: bool = True
    ) -> None:
        """Sync changes to git (admin only)."""
        await interaction.response.defer(thinking=True)

        user_email = self._get_user_email(interaction.user)

        if not self.permission_service.is_admin(user_email):
            embed = create_error_embed(
                "Permission Denied",
                "Only administrators can trigger git sync."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            result = await self.workflow_service.git_sync(
                admin_email=user_email,
                commit_message=commit_message,
                create_pr=create_pr,
            )

            if result.get("success"):
                embed = create_success_embed(
                    "Git Sync Complete",
                    f"Documentation changes have been synced.\n\n"
                    f"**Branch:** {result.get('branch')}\n"
                    f"**Commit:** {result.get('commit_sha', 'N/A')[:8]}"
                )
                if result.get("pr_url"):
                    embed.add_field(
                        name="Pull Request",
                        value=result["pr_url"],
                        inline=False
                    )
            else:
                embed = create_error_embed(
                    "Git Sync Failed",
                    result.get("error", "Unknown error occurred")
                )

            await interaction.followup.send(embed=embed)

        except PermissionError as e:
            embed = create_error_embed("Permission Denied", str(e))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error("git_sync_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed)

    # ==================== Language Preference ====================

    @app_commands.command(
        name="set-language",
        description="Set your preferred language for documentation"
    )
    @app_commands.describe(language="Language code: en (English) or hu (Hungarian)")
    @app_commands.choices(language=[
        app_commands.Choice(name="English", value="en"),
        app_commands.Choice(name="Hungarian (Magyar)", value="hu"),
    ])
    async def set_language(
        self,
        interaction: discord.Interaction,
        language: str
    ) -> None:
        """Set user's language preference."""
        await interaction.response.defer(ephemeral=True)

        try:
            user_email = self._get_user_email(interaction.user)
            lang = self.language_service.parse_language(language)

            if not lang:
                embed = create_error_embed(
                    "Invalid Language",
                    f"Unsupported language: {language}. Use 'en' or 'hu'."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            self.language_service.set_user_preference(user_email, lang)

            embed = create_success_embed(
                "Language Set",
                f"Your language preference has been set to "
                f"**{self.language_service.get_language_name(lang)}**."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error("set_language_error", error=str(e))
            embed = create_error_embed("Error", str(e))
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Setup function for loading the cog."""
    await bot.add_cog(WorkflowCog(bot))
    logger.info("workflow_cog_loaded")
