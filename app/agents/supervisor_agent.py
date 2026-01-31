"""Supervisor agent for managing documentation updates and routing requests."""

import re
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from app.agents.shared import (
    AgentResult,
    AgentStatus,
    AgentType,
    BaseAgent,
    PromptBuilder,
)
from app.config import get_settings
from app.llm import BaseLLMProvider, LLMMessage, LLMOptions, get_llm_provider
from app.utils.logging import get_logger

logger = get_logger(__name__)


class UpdateAction(Enum):
    """Actions the supervisor can take."""

    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_REVIEW = "request_review"
    CLARIFY = "clarify"


class PermissionLevel(Enum):
    """Permission levels for users."""

    ADMIN = "admin"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


class SupervisorAgent(BaseAgent):
    """Agent for supervising documentation updates and request routing."""

    # Keywords that indicate update intent
    UPDATE_KEYWORDS = [
        "update",
        "fix",
        "correct",
        "wrong",
        "incorrect",
        "outdated",
        "change",
        "modify",
        "edit",
        "revise",
        "improve"
    ]

    # Workflow keywords for routing to specific workflows
    WORKFLOW_KEYWORDS = {
        "accept_qa": ["accept", "save answer", "good answer", "helpful answer", "correct answer"],
        "reject_qa": ["reject", "wrong", "incorrect", "escalate", "not helpful", "bad answer"],
        "edit_docs": ["edit docs", "update docs", "change documentation", "modify documentation"],
        "suggest_feature": ["suggest", "feature request", "new feature", "request feature", "idea"],
        "draft_update": ["draft", "propose change", "suggest update", "propose update"],
        "accept_draft": ["accept draft", "approve draft", "apply draft"],
        "git_sync": ["sync", "git sync", "push changes", "commit changes"],
    }

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        """
        Initialize the supervisor agent.

        Args:
            llm_provider: Optional LLM provider instance. If not provided,
                         the default provider from settings will be used.
        """
        super().__init__(AgentType.SUPERVISOR)
        self.settings = get_settings()
        self.system_prompt = self._build_system_prompt()

        # Use injected provider or get default from settings
        self._llm = llm_provider or get_llm_provider()

        logger.info(
            "supervisor_agent_initialized",
            provider=self._llm.provider_name,
            model=self._llm.model_name,
        )

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the supervisor."""
        return PromptBuilder.build_system_prompt(
            role="a supervisor agent responsible for managing documentation updates and ensuring quality",
            capabilities=[
                "Detect when users want to update documentation",
                "Verify user permissions for requested actions",
                "Assess the validity and quality of proposed changes",
                "Route requests to appropriate specialized agents",
                "Make decisions about documentation updates"
            ],
            guidelines=[
                "Only approve updates from authorized users",
                "Ensure proposed changes improve documentation quality",
                "Reject malicious or harmful changes",
                "Request human review for ambiguous cases",
                "Provide clear explanations for decisions",
                "Maintain documentation consistency and accuracy"
            ]
        )

    def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Process a request and determine appropriate action.

        Args:
            input_data: Dictionary containing:
                - message: User message (required)
                - user_id: User identifier (optional)
                - user_permissions: User permission level (optional)
                - context: Additional context (optional)

        Returns:
            AgentResult: Supervisor decision and routing info
        """
        start_time = time.time()
        self._set_status(AgentStatus.PROCESSING)

        try:
            # Validate input
            self._validate_input(input_data, ["message"])

            message = input_data["message"]
            user_id = input_data.get("user_id", "anonymous")
            user_permissions = input_data.get("user_permissions", PermissionLevel.VIEWER.value)
            context = input_data.get("context", "")

            logger.info(
                "supervisor_processing",
                user_id=user_id,
                permissions=user_permissions,
                message_length=len(message)
            )

            # Detect intent
            intent = self._detect_intent(message)

            # Check for workflow request first
            if intent.get("is_workflow_request"):
                decision = self._route_workflow(
                    workflow_type=intent["workflow_type"],
                    message=message,
                    user_id=user_id,
                    user_permissions=user_permissions,
                )
            # If update intent detected, check permissions
            elif intent["is_update_request"]:
                decision = self._evaluate_update_request(
                    message=message,
                    user_permissions=user_permissions,
                    context=context,
                    detected_keywords=intent["keywords"]
                )
            else:
                # Route to appropriate agent
                decision = self._route_request(message, context)

            processing_time = time.time() - start_time
            self._set_status(AgentStatus.COMPLETED)

            logger.info(
                "supervisor_decision_made",
                decision_action=decision["action"],
                processing_time=processing_time
            )

            return AgentResult(
                success=True,
                output=decision,
                metadata={
                    "user_id": user_id,
                    "permissions": user_permissions,
                    "intent": intent["intent_type"]
                },
                processing_time=processing_time
            )

        except Exception as e:
            self._set_status(AgentStatus.FAILED)
            logger.error("supervisor_processing_failed", error=str(e))

            return AgentResult(
                success=False,
                output=None,
                metadata={},
                error=str(e),
                processing_time=time.time() - start_time
            )

    def _detect_intent(self, message: str) -> Dict[str, Any]:
        """
        Detect the intent of a message.

        Args:
            message: User message

        Returns:
            Dict with intent information
        """
        message_lower = message.lower()

        # Check for workflow keywords first (higher priority)
        workflow_intent = self._detect_workflow_intent(message_lower)
        if workflow_intent:
            return {
                "is_update_request": False,
                "is_workflow_request": True,
                "workflow_type": workflow_intent["workflow_type"],
                "keywords": workflow_intent["keywords"],
                "intent_type": f"workflow_{workflow_intent['workflow_type']}",
                "confidence": workflow_intent["confidence"]
            }

        # Check for update keywords
        found_keywords = [
            keyword for keyword in self.UPDATE_KEYWORDS
            if keyword in message_lower
        ]

        is_update = len(found_keywords) > 0

        # Determine intent type
        if is_update:
            intent_type = "documentation_update"
        elif any(word in message_lower for word in ["review", "check my code"]):
            intent_type = "code_review"
        elif any(word in message_lower for word in ["error", "bug", "not working", "help debug"]):
            intent_type = "debugging"
        elif "?" in message:
            intent_type = "question"
        else:
            intent_type = "general"

        return {
            "is_update_request": is_update,
            "is_workflow_request": False,
            "keywords": found_keywords,
            "intent_type": intent_type,
            "confidence": len(found_keywords) / len(self.UPDATE_KEYWORDS) if is_update else 0.5
        }

    def _detect_workflow_intent(self, message_lower: str) -> Optional[Dict[str, Any]]:
        """
        Detect if the message matches a workflow intent.

        Args:
            message_lower: Lowercased message

        Returns:
            Dict with workflow info or None if no match
        """
        best_match = None
        best_score = 0

        for workflow_type, keywords in self.WORKFLOW_KEYWORDS.items():
            matched_keywords = [
                kw for kw in keywords
                if kw in message_lower
            ]

            if matched_keywords:
                # Score based on number of matched keywords and their specificity
                score = sum(len(kw.split()) for kw in matched_keywords)

                if score > best_score:
                    best_score = score
                    best_match = {
                        "workflow_type": workflow_type,
                        "keywords": matched_keywords,
                        "confidence": min(0.9, 0.5 + (score * 0.1))
                    }

        return best_match

    def _evaluate_update_request(
        self,
        message: str,
        user_permissions: str,
        context: str,
        detected_keywords: List[str]
    ) -> Dict[str, Any]:
        """
        Evaluate whether to approve a documentation update request.

        Args:
            message: User message
            user_permissions: User's permission level
            context: Additional context
            detected_keywords: Update keywords found

        Returns:
            Dict with evaluation decision
        """
        # Check permissions first
        permission_level = PermissionLevel(user_permissions)

        if permission_level == PermissionLevel.VIEWER:
            return {
                "action": UpdateAction.REJECT.value,
                "reason": "Insufficient permissions. Only contributors and admins can update documentation.",
                "suggested_action": "Contact an administrator for update access.",
                "requires_human_review": False
            }

        # Use LLM to assess update quality and validity
        prompt = f"""
Evaluate this documentation update request:

**Request:** {message}

**Context:** {context}

**Detected Intent:** Update documentation (keywords: {', '.join(detected_keywords)})

Determine if this update should be:
1. APPROVED - High quality, valid improvement
2. REJECTED - Invalid, harmful, or low quality
3. REQUEST_REVIEW - Needs human review (ambiguous or significant change)

Consider:
- Is the proposed change accurate and helpful?
- Does it improve documentation quality?
- Is it clear what should be updated?
- Are there any concerns about the change?

Respond with:
- Decision: [APPROVE/REJECT/REQUEST_REVIEW]
- Confidence: [0-1]
- Reason: [Brief explanation]
- Concerns: [Any concerns, if applicable]
"""

        try:
            messages = [
                LLMMessage(role="system", content=self.system_prompt),
                LLMMessage(role="user", content=prompt),
            ]
            options = LLMOptions(temperature=0.3)

            response = self._llm.chat(messages, options)
            evaluation = response.content

            # Parse LLM response
            decision = self._parse_evaluation(evaluation)

            # Override based on permission level
            if permission_level == PermissionLevel.CONTRIBUTOR and decision["action"] == UpdateAction.APPROVE.value:
                # Contributors need admin approval for major changes
                if decision.get("confidence", 0) < 0.8:
                    decision["action"] = UpdateAction.REQUEST_REVIEW.value
                    decision["reason"] += " (Admin approval required for this change)"

            return decision

        except Exception as e:
            logger.error("update_evaluation_failed", error=str(e))

            # Default to requiring review on error
            return {
                "action": UpdateAction.REQUEST_REVIEW.value,
                "reason": f"Unable to automatically evaluate update: {str(e)}",
                "suggested_action": "Request human review",
                "requires_human_review": True
            }

    def _parse_evaluation(self, evaluation: str) -> Dict[str, Any]:
        """
        Parse LLM evaluation response.

        Args:
            evaluation: LLM response text

        Returns:
            Dict with parsed decision
        """
        evaluation_upper = evaluation.upper()

        # Determine action
        if "APPROVE" in evaluation_upper:
            action = UpdateAction.APPROVE.value
        elif "REJECT" in evaluation_upper:
            action = UpdateAction.REJECT.value
        else:
            action = UpdateAction.REQUEST_REVIEW.value

        # Extract confidence
        confidence_match = re.search(r"confidence[:\s]+([0-9.]+)", evaluation, re.IGNORECASE)
        confidence = float(confidence_match.group(1)) if confidence_match else 0.5

        # Extract reason
        reason_match = re.search(r"reason[:\s]+(.+?)(?:\n|$)", evaluation, re.IGNORECASE)
        reason = reason_match.group(1).strip() if reason_match else evaluation[:200]

        return {
            "action": action,
            "confidence": confidence,
            "reason": reason,
            "full_evaluation": evaluation,
            "requires_human_review": action == UpdateAction.REQUEST_REVIEW.value
        }

    def _route_request(self, message: str, context: str) -> Dict[str, Any]:
        """
        Route a non-update request to appropriate agent.

        Args:
            message: User message
            context: Additional context

        Returns:
            Dict with routing decision
        """
        message_lower = message.lower()

        # Determine target agent
        if any(word in message_lower for word in ["review", "check", "code"]):
            target_agent = "code_review"
            reason = "Message contains code review keywords"
        elif any(word in message_lower for word in ["error", "bug", "debug", "problem", "not working"]):
            target_agent = "debug"
            reason = "Message indicates debugging need"
        elif any(word in message_lower for word in ["configure", "config", "setup", "settings"]):
            target_agent = "config_checker"
            reason = "Message relates to configuration"
        else:
            target_agent = "qa"
            reason = "General question or request"

        return {
            "action": "route",
            "target_agent": target_agent,
            "reason": reason,
            "confidence": 0.8,
            "requires_human_review": False
        }

    def _route_workflow(
        self,
        workflow_type: str,
        message: str,
        user_id: str,
        user_permissions: str,
    ) -> Dict[str, Any]:
        """
        Route to a workflow based on detected intent.

        Args:
            workflow_type: Type of workflow detected
            message: Original user message
            user_id: User identifier
            user_permissions: User's permission level

        Returns:
            Dict with workflow routing decision
        """
        # Define admin-only workflows
        admin_workflows = {"edit_docs", "accept_draft", "git_sync"}

        # Check if admin permission required
        if workflow_type in admin_workflows:
            from app.services.permission_service import get_permission_service
            permission_service = get_permission_service()

            if not permission_service.is_admin(user_id):
                return {
                    "action": "permission_denied",
                    "workflow_type": workflow_type,
                    "reason": f"The '{workflow_type}' workflow requires admin permissions.",
                    "confidence": 1.0,
                    "requires_human_review": False
                }

        # Map workflow types to their descriptions
        workflow_descriptions = {
            "accept_qa": "Accept the last Q&A answer and save to documentation",
            "reject_qa": "Reject the last answer and escalate to admins",
            "edit_docs": "Edit documentation based on instruction",
            "suggest_feature": "Submit a feature suggestion",
            "draft_update": "Create a draft update for admin review",
            "accept_draft": "Accept and apply a draft update",
            "git_sync": "Sync changes to git repository",
        }

        return {
            "action": "workflow",
            "workflow_type": workflow_type,
            "description": workflow_descriptions.get(workflow_type, "Execute workflow"),
            "message": message,
            "user_id": user_id,
            "reason": f"Detected {workflow_type} intent in message",
            "confidence": 0.85,
            "requires_human_review": False
        }

    def check_permissions(self, user_id: str, required_permission: PermissionLevel) -> bool:
        """
        Check if a user has required permission level.

        Args:
            user_id: User identifier
            required_permission: Required permission level

        Returns:
            bool: True if user has permission

        Note:
            In production, this should query Azure AD or permission database
        """
        # TODO: Implement actual permission checking via Azure AD
        # For now, return False for safety
        logger.warning(
            "permission_check_not_implemented",
            user_id=user_id,
            required=required_permission.value
        )
        return False


# Global instance
_supervisor_agent: Optional[SupervisorAgent] = None


def get_supervisor_agent() -> SupervisorAgent:
    """
    Get or create a global supervisor agent instance.

    Returns:
        SupervisorAgent: The supervisor agent
    """
    global _supervisor_agent
    if _supervisor_agent is None:
        _supervisor_agent = SupervisorAgent()
    return _supervisor_agent
