"""Workflow service for orchestrating documentation management workflows."""

import asyncio
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from app.config import get_settings
from app.events import DocumentEvent, EventData, get_event_dispatcher
from app.services.permission_service import get_permission_service, PermissionService
from app.services.language_service import get_language_service, LanguageService
from app.services.git_service import get_git_service, GitService
from app.services.notification_service import get_notification_service, NotificationService
from app.storage.models import (
    DraftUpdate,
    DraftStatus,
    PendingQuestion,
    QuestionStatus,
    FeatureSuggestion,
    AcceptedQA,
    Language,
)
from app.storage.repositories import (
    get_draft_repository,
    get_queue_repository,
    get_feature_repository,
    DraftRepository,
    QueueRepository,
    FeatureRepository,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


class WorkflowService:
    """Service for orchestrating all documentation management workflows."""

    def __init__(
        self,
        permission_service: Optional[PermissionService] = None,
        language_service: Optional[LanguageService] = None,
        git_service: Optional[GitService] = None,
        notification_service: Optional[NotificationService] = None,
        draft_repository: Optional[DraftRepository] = None,
        queue_repository: Optional[QueueRepository] = None,
        feature_repository: Optional[FeatureRepository] = None,
    ):
        """
        Initialize workflow service.

        Args:
            permission_service: Permission service instance
            language_service: Language service instance
            git_service: Git service instance
            notification_service: Notification service instance
            draft_repository: Draft repository instance
            queue_repository: Queue repository instance
            feature_repository: Feature repository instance
        """
        self.settings = get_settings()
        self.permission_service = permission_service or get_permission_service()
        self.language_service = language_service or get_language_service()
        self.git_service = git_service or get_git_service()
        self.notification_service = notification_service or get_notification_service()
        self.draft_repo = draft_repository or get_draft_repository()
        self.queue_repo = queue_repository or get_queue_repository()
        self.feature_repo = feature_repository or get_feature_repository()
        self.event_dispatcher = get_event_dispatcher()

        logger.info("workflow_service_initialized")

    async def _emit_event(self, event: EventData) -> None:
        """
        Emit an event to the event dispatcher.

        Args:
            event: The event to emit
        """
        try:
            await self.event_dispatcher.emit(event)
        except Exception as e:
            logger.error("event_emission_failed", event_type=event.event_type.value, error=str(e))

    # ==================== Workflow 1: Q&A Acceptance ====================

    async def accept_qa(
        self,
        question: str,
        answer: str,
        user_email: str,
        language: str = "en",
        sources: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Accept a Q&A answer and save it to documentation.

        Workflow 1: Question -> Answer -> Accept -> Save to docs

        Args:
            question: The question
            answer: The accepted answer
            user_email: User's email address
            language: Language code (en/hu)
            sources: Optional list of source references

        Returns:
            Dictionary with acceptance result
        """
        lang = self.language_service.parse_language(language) or Language.EN

        # Create accepted Q&A record
        qa = AcceptedQA(
            question=question,
            answer=answer,
            user_email=user_email,
            language=lang.value,
            sources=sources or [],
        )

        # Get Q&A file path
        qa_file = self.language_service.get_qa_file_path(lang)

        # Ensure directory exists
        qa_file.parent.mkdir(parents=True, exist_ok=True)

        # Append to Q&A file
        try:
            markdown = qa.to_markdown()

            # Create file with header if it doesn't exist
            if not qa_file.exists():
                header = f"# Accepted Q&A ({self.language_service.get_language_name(lang)})\n\n"
                header += "_This file contains accepted Q&A pairs from user interactions._\n\n---\n\n"
                qa_file.write_text(header, encoding="utf-8")

            # Append Q&A
            with open(qa_file, "a", encoding="utf-8") as f:
                f.write(markdown)

            logger.info(
                "qa_accepted",
                qa_id=qa.id,
                language=lang.value,
                file=str(qa_file)
            )

            # Emit DOC_UPDATED event for the Q&A file
            await self._emit_event(EventData(
                event_type=DocumentEvent.DOC_UPDATED,
                source="workflow_service",
                user_email=user_email,
                file_path=str(qa_file),
                metadata={"qa_id": qa.id, "language": lang.value},
            ))

            return {
                "success": True,
                "qa_id": qa.id,
                "message": f"Q&A saved to {qa_file.name}",
                "file_path": str(qa_file),
            }

        except Exception as e:
            logger.error("qa_acceptance_failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to save Q&A to documentation",
            }

    def get_accepted_qa(self, qa_id: str, language: str = "en") -> Optional[dict[str, Any]]:
        """
        Get an accepted Q&A by ID from the documentation file.

        Args:
            qa_id: The Q&A ID (e.g., QA-5D18ECF2)
            language: Language code (en/hu)

        Returns:
            Dictionary with Q&A details or None if not found
        """
        import re

        # Normalize ID
        normalized_id = qa_id.upper()
        if not normalized_id.startswith("QA-"):
            normalized_id = f"QA-{normalized_id}"

        lang = self.language_service.parse_language(language) or Language.EN
        qa_file = self.language_service.get_qa_file_path(lang)

        if not qa_file.exists():
            return None

        try:
            content = qa_file.read_text(encoding="utf-8")

            # Search for the QA ID in the file
            # Pattern: ### Question\n<!-- QA_ID: QA-XXXXXXXX -->\n\nAnswer...\n\n_ID: QA-XXXXXXXX | Accepted on YYYY-MM-DD_
            pattern = rf"### (.*?)\n<!-- QA_ID: {re.escape(normalized_id)} -->\n\n(.*?)\n\n_ID: {re.escape(normalized_id)} \| Accepted on (\d{{4}}-\d{{2}}-\d{{2}})_"
            match = re.search(pattern, content, re.DOTALL)

            if match:
                return {
                    "id": normalized_id,
                    "question": match.group(1).strip(),
                    "answer": match.group(2).strip(),
                    "accepted_on": match.group(3),
                    "language": lang.value,
                    "file_path": str(qa_file),
                }

            # Fallback: Search for older format without ID comment
            # Pattern: ### Question\n\nAnswer...\n\n_Accepted on YYYY-MM-DD_
            # This won't match by ID but we can inform the user

            return None

        except Exception as e:
            logger.error("get_accepted_qa_failed", qa_id=qa_id, error=str(e))
            return None

    def list_accepted_qa(self, language: str = "en", limit: int = 10) -> list[dict[str, Any]]:
        """
        List recent accepted Q&A pairs from the documentation file.

        Args:
            language: Language code (en/hu)
            limit: Maximum number of Q&A pairs to return

        Returns:
            List of Q&A dictionaries
        """
        import re

        lang = self.language_service.parse_language(language) or Language.EN
        qa_file = self.language_service.get_qa_file_path(lang)

        if not qa_file.exists():
            return []

        try:
            content = qa_file.read_text(encoding="utf-8")

            # Pattern to match Q&A entries with IDs
            pattern = r"### (.*?)\n<!-- QA_ID: (QA-[A-F0-9]+) -->\n\n(.*?)\n\n_ID: QA-[A-F0-9]+ \| Accepted on (\d{4}-\d{2}-\d{2})_"
            matches = list(re.finditer(pattern, content, re.DOTALL))

            # Return most recent first (assuming they're appended)
            results = []
            for match in reversed(matches[-limit:]):
                results.append({
                    "id": match.group(2),
                    "question": match.group(1).strip()[:100] + ("..." if len(match.group(1)) > 100 else ""),
                    "accepted_on": match.group(4),
                })

            return results

        except Exception as e:
            logger.error("list_accepted_qa_failed", error=str(e))
            return []

    # ==================== Workflow 2: Q&A Escalation ====================

    async def escalate_question(
        self,
        question: str,
        bot_answer: str,
        user_email: str,
        rejection_reason: Optional[str] = None,
        platform: str = "api",
        conversation_id: Optional[str] = None,
        language: str = "en",
    ) -> dict[str, Any]:
        """
        Escalate a rejected question to the admin queue.

        Workflow 2: Question -> Answer rejected -> Notify admins

        Args:
            question: The question
            bot_answer: The bot's answer that was rejected
            user_email: User's email address
            rejection_reason: Optional reason for rejection
            platform: Platform where the question originated
            conversation_id: Optional conversation ID for follow-up
            language: Language code

        Returns:
            Dictionary with escalation result
        """
        # Create pending question
        pending = PendingQuestion(
            user_email=user_email,
            question=question,
            bot_answer=bot_answer,
            rejection_reason=rejection_reason,
            platform=platform,
            conversation_id=conversation_id,
            language=language,
        )

        # Save to queue
        self.queue_repo.add(pending)

        # Notify admins
        await self.notification_service.notify_question_escalated(pending)

        # Emit question created event
        await self._emit_event(EventData(
            event_type=DocumentEvent.QUESTION_CREATED,
            source="workflow_service",
            user_email=user_email,
            question_id=pending.id,
            question_text=question,
            metadata={
                "platform": platform,
                "rejection_reason": rejection_reason,
                "language": language,
            },
        ))

        logger.info(
            "question_escalated",
            question_id=pending.id,
            platform=platform,
            user=user_email
        )

        return {
            "success": True,
            "question_id": pending.id,
            "message": "Question escalated to admin queue. An administrator will review it shortly.",
        }

    async def respond_to_question(
        self,
        question_id: str,
        admin_email: str,
        response: str,
        action: str = "answer",
    ) -> dict[str, Any]:
        """
        Admin responds to an escalated question.

        Args:
            question_id: The question ID
            admin_email: Admin's email address
            response: Admin's response
            action: Action to take (answer, on_hold, close)

        Returns:
            Dictionary with response result
        """
        self.permission_service.require_admin(admin_email, "respond to questions")

        if action == "answer":
            question = self.queue_repo.respond(question_id, admin_email, response)
        elif action == "on_hold":
            question = self.queue_repo.put_on_hold(question_id)
        else:
            question = self.queue_repo.get(question_id)

        if not question:
            return {
                "success": False,
                "error": f"Question {question_id} not found",
            }

        # Emit question answered event if this was an answer action
        if action == "answer":
            await self._emit_event(EventData(
                event_type=DocumentEvent.QUESTION_ANSWERED,
                source="workflow_service",
                user_email=admin_email,
                question_id=question_id,
                question_text=question.question,
                answer_text=response,
                metadata={
                    "original_user": question.user_email,
                    "platform": question.platform,
                },
            ))

        logger.info(
            "question_responded",
            question_id=question_id,
            action=action,
            admin=admin_email
        )

        return {
            "success": True,
            "question_id": question_id,
            "action": action,
            "message": f"Question {action}ed successfully",
        }

    def get_pending_questions(self) -> list[PendingQuestion]:
        """Get all pending questions for admin review."""
        return self.queue_repo.get_pending()

    # ==================== Workflow 3: Edit Docs (Admin) ====================

    async def edit_docs(
        self,
        instruction: str,
        admin_email: str,
        target_file: Optional[str] = None,
        language: str = "en",
        commit_changes: bool = True,
    ) -> dict[str, Any]:
        """
        Admin edits documentation based on natural language instruction.

        Workflow 3: Admin instruction -> Bot interprets -> Edit docs

        Args:
            instruction: Natural language edit instruction
            admin_email: Admin's email address
            target_file: Optional specific file to edit
            language: Language code
            commit_changes: Whether to commit changes to git

        Returns:
            Dictionary with edit result
        """
        self.permission_service.require_admin(admin_email, "edit documentation")

        lang = self.language_service.parse_language(language) or Language.EN

        # Determine target path
        if target_file:
            target_path = Path(target_file)
        else:
            target_path = self.language_service.get_docs_path(lang)

        # TODO: Implement LLM-based instruction interpretation
        # For now, this is a placeholder that would integrate with the LLM
        # to interpret the instruction and make appropriate edits

        logger.info(
            "docs_edit_requested",
            admin=admin_email,
            instruction=instruction[:100],
            target=str(target_path)
        )

        return {
            "success": True,
            "message": "Documentation edit requested. This feature requires LLM integration.",
            "instruction": instruction,
            "target_path": str(target_path),
            "note": "Full implementation pending LLM agent integration",
        }

    # ==================== Workflow 4: Feature Suggestion ====================

    async def suggest_feature(
        self,
        title: str,
        description: str,
        user_email: str,
        language: str = "en",
    ) -> dict[str, Any]:
        """
        Submit a feature suggestion.

        Workflow 4: User suggests feature -> Save to suggestions file

        Args:
            title: Feature title
            description: Feature description
            user_email: User's email address
            language: Language code

        Returns:
            Dictionary with suggestion result
        """
        # Create feature suggestion
        feature = FeatureSuggestion(
            user_email=user_email,
            title=title,
            description=description,
            language=language,
        )

        # Save to repository
        self.feature_repo.add(feature)

        # Update suggestions file
        suggestions_file = self.language_service.get_suggestions_file_path()
        suggestions_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Create file with header if it doesn't exist
            if not suggestions_file.exists():
                header = "# Feature Suggestions\n\n"
                header += "_Community suggestions for new features and improvements._\n\n---\n\n"
                suggestions_file.write_text(header, encoding="utf-8")

            # Append suggestion
            suggestion_md = f"""## {feature.id}: {title}

**Submitted by:** {user_email}
**Date:** {feature.created_at[:10]}
**Language:** {language.upper()}

{description}

---

"""
            with open(suggestions_file, "a", encoding="utf-8") as f:
                f.write(suggestion_md)

            logger.info(
                "feature_suggested",
                feature_id=feature.id,
                title=title,
                user=user_email
            )

            return {
                "success": True,
                "feature_id": feature.id,
                "message": f"Feature suggestion '{title}' submitted successfully.",
                "file_path": str(suggestions_file),
            }

        except Exception as e:
            logger.error("feature_suggestion_failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to save feature suggestion",
            }

    def get_features(self, status: Optional[str] = None) -> list[FeatureSuggestion]:
        """Get feature suggestions, optionally filtered by status."""
        if status:
            from app.storage.models import FeatureStatus
            return self.feature_repo.get_by_status(FeatureStatus(status))
        return self.feature_repo.get_all()

    # ==================== Workflow 5: Draft Update ====================

    async def create_draft_update(
        self,
        content: str,
        target_section: str,
        user_email: str,
        description: Optional[str] = None,
        language: str = "en",
    ) -> dict[str, Any]:
        """
        Create a draft documentation update.

        Workflow 5: User submits draft -> Save for admin review

        Args:
            content: Draft content
            target_section: Target documentation section
            user_email: User's email address
            description: Optional description of the change
            language: Language code

        Returns:
            Dictionary with draft creation result
        """
        # Create draft
        draft = DraftUpdate(
            user_email=user_email,
            content=content,
            target_section=target_section,
            description=description or "",
            language=language,
        )

        # Save to repository
        self.draft_repo.add(draft)

        # Update drafts file
        drafts_file = self.language_service.get_drafts_file_path()
        drafts_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Create file with header if it doesn't exist
            if not drafts_file.exists():
                header = "# Draft Updates\n\n"
                header += "_Pending documentation updates awaiting admin approval._\n\n---\n\n"
                drafts_file.write_text(header, encoding="utf-8")

            # Append draft
            draft_md = f"""## {draft.id}: {target_section}

**Status:** {draft.status.upper()}
**Submitted by:** {user_email}
**Date:** {draft.created_at[:10]}
**Language:** {language.upper()}

### Description
{description or 'No description provided.'}

### Content
```
{content[:1000]}{"..." if len(content) > 1000 else ""}
```

---

"""
            with open(drafts_file, "a", encoding="utf-8") as f:
                f.write(draft_md)

            # Notify admins
            await self.notification_service.notify_draft_submitted(draft)

            # Emit draft created event
            await self._emit_event(EventData(
                event_type=DocumentEvent.DRAFT_CREATED,
                source="workflow_service",
                user_email=user_email,
                draft_id=draft.id,
                draft_content=content,
                target_section=target_section,
                metadata={"description": description, "language": language},
            ))

            logger.info(
                "draft_created",
                draft_id=draft.id,
                target=target_section,
                user=user_email
            )

            return {
                "success": True,
                "draft_id": draft.id,
                "message": f"Draft update '{draft.id}' created successfully and submitted for review.",
                "file_path": str(drafts_file),
            }

        except Exception as e:
            logger.error("draft_creation_failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create draft update",
            }

    def get_drafts(self, status: Optional[str] = None) -> list[DraftUpdate]:
        """Get draft updates, optionally filtered by status."""
        if status:
            return self.draft_repo.get_by_status(DraftStatus(status))
        return self.draft_repo.get_all()

    def get_pending_drafts(self) -> list[DraftUpdate]:
        """Get all pending drafts for admin review."""
        return self.draft_repo.get_pending()

    # ==================== Workflow 6: Accept Draft (Admin) ====================

    async def accept_draft(
        self,
        draft_id: str,
        admin_email: str,
        apply_immediately: bool = True,
        commit_changes: bool = True,
    ) -> dict[str, Any]:
        """
        Admin accepts and optionally applies a draft update.

        Workflow 6: Admin accepts draft -> Apply to docs -> Commit to git

        Args:
            draft_id: The draft ID
            admin_email: Admin's email address
            apply_immediately: Whether to apply the draft immediately
            commit_changes: Whether to commit changes to git

        Returns:
            Dictionary with acceptance result
        """
        self.permission_service.require_admin(admin_email, "accept draft updates")

        draft = self.draft_repo.get(draft_id)
        if not draft:
            return {
                "success": False,
                "error": f"Draft {draft_id} not found",
            }

        # Approve the draft
        self.draft_repo.approve(draft_id, admin_email)

        result = {
            "success": True,
            "draft_id": draft_id,
            "approved": True,
            "applied": False,
            "git_commit": None,
            "message": f"Draft {draft_id} approved by {admin_email}",
        }

        if apply_immediately:
            # Apply the draft content to the target section
            apply_result = await self._apply_draft(draft)
            result["applied"] = apply_result["success"]

            if apply_result["success"]:
                self.draft_repo.mark_applied(draft_id)
                result["message"] = f"Draft {draft_id} approved and applied to documentation."

                # Commit to git if enabled
                if commit_changes and self.git_service.is_enabled():
                    git_result = self.git_service.sync_changes(
                        files=[apply_result.get("file_path", "")],
                        commit_message=f"Apply draft {draft_id}: {draft.description or draft.target_section}",
                        branch_name=f"docs/draft-{draft_id.lower()}",
                        create_pr=True
                    )
                    result["git_commit"] = git_result.get("commit_sha")
                    result["pr_url"] = git_result.get("pr_url")

        # Emit draft approved event
        await self._emit_event(EventData(
            event_type=DocumentEvent.DRAFT_APPROVED,
            source="workflow_service",
            user_email=admin_email,
            draft_id=draft_id,
            target_section=draft.target_section,
            file_path=result.get("file_path"),
            metadata={"applied": result["applied"]},
        ))

        logger.info(
            "draft_accepted",
            draft_id=draft_id,
            admin=admin_email,
            applied=result["applied"]
        )

        return result

    async def reject_draft(
        self,
        draft_id: str,
        admin_email: str,
        reason: str,
    ) -> dict[str, Any]:
        """
        Admin rejects a draft update.

        Args:
            draft_id: The draft ID
            admin_email: Admin's email address
            reason: Reason for rejection

        Returns:
            Dictionary with rejection result
        """
        self.permission_service.require_admin(admin_email, "reject draft updates")

        draft = self.draft_repo.reject(draft_id, reason)
        if not draft:
            return {
                "success": False,
                "error": f"Draft {draft_id} not found",
            }

        # Emit draft rejected event
        await self._emit_event(EventData(
            event_type=DocumentEvent.DRAFT_REJECTED,
            source="workflow_service",
            user_email=admin_email,
            draft_id=draft_id,
            target_section=draft.target_section,
            metadata={"reason": reason},
        ))

        logger.info(
            "draft_rejected",
            draft_id=draft_id,
            admin=admin_email,
            reason=reason
        )

        return {
            "success": True,
            "draft_id": draft_id,
            "message": f"Draft {draft_id} rejected: {reason}",
        }

    async def _apply_draft(self, draft: DraftUpdate) -> dict[str, Any]:
        """
        Apply a draft's content to the target documentation.

        Args:
            draft: The draft to apply

        Returns:
            Dictionary with application result
        """
        # Parse target section to determine file and location
        target = draft.target_section
        lang = self.language_service.parse_language(draft.language) or Language.EN

        # Determine target file
        if "/" in target or "\\" in target:
            # Full path specified
            target_file = Path(self.settings.docs_repo_path).parent / target
        else:
            # Just filename, use language-specific docs folder
            target_file = self.language_service.get_docs_path(lang) / target

        try:
            # Ensure directory exists
            target_file.parent.mkdir(parents=True, exist_ok=True)

            # For now, append content to file (simple implementation)
            # More sophisticated implementation would parse the file and
            # replace/insert at specific sections

            if target_file.exists():
                # Append to existing file with separator
                with open(target_file, "a", encoding="utf-8") as f:
                    f.write(f"\n\n{draft.content}\n")
            else:
                # Create new file
                target_file.write_text(draft.content, encoding="utf-8")

            logger.info(
                "draft_applied",
                draft_id=draft.id,
                file=str(target_file)
            )

            # Emit DOC_UPDATED event for the target file
            await self._emit_event(EventData(
                event_type=DocumentEvent.DOC_UPDATED,
                source="workflow_service",
                file_path=str(target_file),
                draft_id=draft.id,
                metadata={"language": draft.language},
            ))

            return {
                "success": True,
                "file_path": str(target_file),
            }

        except Exception as e:
            logger.error("draft_application_failed", error=str(e), draft_id=draft.id)
            return {
                "success": False,
                "error": str(e),
            }

    # ==================== Git Sync (Admin) ====================

    async def git_sync(
        self,
        admin_email: str,
        commit_message: Optional[str] = None,
        branch_name: Optional[str] = None,
        create_pr: bool = True,
    ) -> dict[str, Any]:
        """
        Sync all changes to git repository.

        Args:
            admin_email: Admin's email address
            commit_message: Optional custom commit message
            branch_name: Optional branch name
            create_pr: Whether to create a pull request

        Returns:
            Dictionary with sync result
        """
        self.permission_service.require_admin(admin_email, "trigger git sync")

        if not self.git_service.is_enabled():
            return {
                "success": False,
                "error": "Git operations are disabled. Set DOCS_GIT_ENABLED=true.",
            }

        # Generate branch name if not provided
        if not branch_name:
            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            branch_name = f"docs/update-{timestamp}"

        # Generate commit message if not provided
        if not commit_message:
            commit_message = f"Documentation update by {admin_email}"

        # Get all documentation files that might have changed
        docs_path = Path(self.settings.docs_repo_path)
        kb_path = docs_path.parent

        # Collect all files in knowledge base
        files = []
        for pattern in ["**/*.md", "**/*.txt"]:
            files.extend([str(f) for f in kb_path.glob(pattern)])

        # Emit GIT_SYNC_REQUESTED event
        await self._emit_event(EventData(
            event_type=DocumentEvent.GIT_SYNC_REQUESTED,
            source="workflow_service",
            user_email=admin_email,
            branch_name=branch_name,
            metadata={"commit_message": commit_message, "create_pr": create_pr},
        ))

        # Sync changes
        result = self.git_service.sync_changes(
            files=files,
            commit_message=commit_message,
            branch_name=branch_name,
            create_pr=create_pr
        )

        logger.info(
            "git_sync_complete",
            admin=admin_email,
            success=result.get("success"),
            branch=result.get("branch")
        )

        return result


# Global instance
_workflow_service: Optional[WorkflowService] = None


@lru_cache()
def get_workflow_service() -> WorkflowService:
    """
    Get or create a global workflow service instance.

    Returns:
        WorkflowService: The workflow service
    """
    global _workflow_service
    if _workflow_service is None:
        _workflow_service = WorkflowService()
    return _workflow_service
