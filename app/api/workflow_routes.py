"""API routes for documentation management workflows."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Query

from app.api.schemas import (
    # Q&A
    QAAcceptRequest,
    QAAcceptResponse,
    QARejectRequest,
    QARejectResponse,
    # Edit Docs
    EditDocsRequest,
    EditDocsResponse,
    # Feature Suggestion
    FeatureSuggestionRequest,
    FeatureSuggestionResponse,
    FeatureSuggestionItem,
    FeatureListResponse,
    # Draft Update
    DraftUpdateRequest,
    DraftUpdateResponse,
    DraftItem,
    DraftListResponse,
    AcceptDraftRequest,
    AcceptDraftResponse,
    RejectDraftRequest,
    RejectDraftResponse,
    # Queue
    PendingQuestionItem,
    QueueResponse,
    QueueRespondRequest,
    QueueRespondResponse,
    # Git
    GitSyncRequest,
    GitSyncResponse,
    # Language
    SetLanguageRequest,
    SetLanguageResponse,
    # Error
    ErrorResponse,
)
from app.services.workflow_service import get_workflow_service
from app.services.permission_service import get_permission_service
from app.services.language_service import get_language_service
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/workflow", tags=["workflow"])


def get_user_email(x_user_email: Optional[str] = Header(None)) -> str:
    """
    Extract user email from header.

    In production, this would validate against an auth token.
    For now, we require the X-User-Email header.
    """
    if not x_user_email:
        raise HTTPException(
            status_code=401,
            detail="X-User-Email header required"
        )
    return x_user_email


# ==================== Q&A Workflow ====================

@router.post(
    "/qa/accept",
    response_model=QAAcceptResponse,
    summary="Accept Q&A answer",
    description="Accept a Q&A answer and save it to the documentation."
)
async def accept_qa(
    request: QAAcceptRequest,
    x_user_email: str = Header(..., description="User email address")
) -> QAAcceptResponse:
    """Accept Q&A answer and save to documentation."""
    workflow = get_workflow_service()

    result = await workflow.accept_qa(
        question=request.question,
        answer=request.answer,
        user_email=x_user_email,
        language=request.language,
        sources=request.sources,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to save Q&A")
        )

    return QAAcceptResponse(
        success=True,
        qa_id=result.get("qa_id"),
        message=result.get("message", "Q&A saved successfully"),
        file_path=result.get("file_path"),
    )


@router.post(
    "/qa/reject",
    response_model=QARejectResponse,
    summary="Reject Q&A answer",
    description="Reject a Q&A answer and escalate to admin queue."
)
async def reject_qa(
    request: QARejectRequest,
    x_user_email: str = Header(..., description="User email address")
) -> QARejectResponse:
    """Reject Q&A answer and escalate to admin queue."""
    workflow = get_workflow_service()

    result = await workflow.escalate_question(
        question=request.question,
        bot_answer=request.answer,
        user_email=x_user_email,
        rejection_reason=request.reason,
        platform=request.platform,
        conversation_id=request.conversation_id,
        language=request.language,
    )

    return QARejectResponse(
        success=result.get("success", False),
        question_id=result.get("question_id"),
        message=result.get("message", "Question escalated"),
    )


# ==================== Edit Docs (Admin) ====================

@router.post(
    "/edit-docs",
    response_model=EditDocsResponse,
    summary="Edit documentation (Admin)",
    description="Edit documentation based on natural language instruction. Admin only."
)
async def edit_docs(
    request: EditDocsRequest,
    x_user_email: str = Header(..., description="Admin email address")
) -> EditDocsResponse:
    """Edit documentation (admin only)."""
    workflow = get_workflow_service()

    try:
        result = await workflow.edit_docs(
            instruction=request.instruction,
            admin_email=x_user_email,
            target_file=request.target_file,
            language=request.language,
            commit_changes=request.commit_changes,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    return EditDocsResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        changes_made=result.get("changes_made"),
        files_modified=result.get("files_modified"),
        git_commit_sha=result.get("git_commit_sha"),
    )


# ==================== Feature Suggestion ====================

@router.post(
    "/suggest-feature",
    response_model=FeatureSuggestionResponse,
    summary="Submit feature suggestion",
    description="Submit a feature suggestion for the documentation or framework."
)
async def suggest_feature(
    request: FeatureSuggestionRequest,
    x_user_email: str = Header(..., description="User email address")
) -> FeatureSuggestionResponse:
    """Submit a feature suggestion."""
    workflow = get_workflow_service()

    result = await workflow.suggest_feature(
        title=request.title,
        description=request.description,
        user_email=x_user_email,
        language=request.language,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to save feature suggestion")
        )

    return FeatureSuggestionResponse(
        success=True,
        feature_id=result.get("feature_id"),
        message=result.get("message", "Feature suggestion submitted"),
    )


@router.get(
    "/features",
    response_model=FeatureListResponse,
    summary="List feature suggestions",
    description="Get list of feature suggestions."
)
async def list_features(
    status: Optional[str] = Query(None, description="Filter by status")
) -> FeatureListResponse:
    """List feature suggestions."""
    workflow = get_workflow_service()
    features = workflow.get_features(status=status)

    items = [
        FeatureSuggestionItem(
            id=f.id,
            title=f.title,
            description=f.description,
            user_email=f.user_email,
            language=f.language,
            status=f.status,
            votes=f.votes,
            created_at=f.created_at,
        )
        for f in features
    ]

    return FeatureListResponse(
        features=items,
        total_count=len(items),
    )


# ==================== Draft Update ====================

@router.post(
    "/draft-update",
    response_model=DraftUpdateResponse,
    summary="Create draft update",
    description="Create a draft documentation update for admin review."
)
async def create_draft_update(
    request: DraftUpdateRequest,
    x_user_email: str = Header(..., description="User email address")
) -> DraftUpdateResponse:
    """Create a draft documentation update."""
    workflow = get_workflow_service()

    result = await workflow.create_draft_update(
        content=request.content,
        target_section=request.target_section,
        user_email=x_user_email,
        description=request.description,
        language=request.language,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to create draft")
        )

    return DraftUpdateResponse(
        success=True,
        draft_id=result.get("draft_id"),
        message=result.get("message", "Draft created successfully"),
    )


@router.get(
    "/drafts",
    response_model=DraftListResponse,
    summary="List draft updates",
    description="Get list of draft updates. Admin only for full list."
)
async def list_drafts(
    status: Optional[str] = Query(None, description="Filter by status"),
    x_user_email: str = Header(..., description="User email address")
) -> DraftListResponse:
    """List draft updates."""
    workflow = get_workflow_service()
    permission = get_permission_service()

    # Non-admins can only see their own drafts
    if permission.is_admin(x_user_email):
        drafts = workflow.get_drafts(status=status)
    else:
        all_drafts = workflow.get_drafts(status=status)
        drafts = [d for d in all_drafts if d.user_email == x_user_email]

    items = [
        DraftItem(
            id=d.id,
            user_email=d.user_email,
            content=d.content[:200] + ("..." if len(d.content) > 200 else ""),
            target_section=d.target_section,
            description=d.description or "",
            language=d.language,
            status=d.status,
            created_at=d.created_at,
        )
        for d in drafts
    ]

    pending = workflow.get_pending_drafts()

    return DraftListResponse(
        drafts=items,
        total_count=len(items),
        pending_count=len(pending) if permission.is_admin(x_user_email) else 0,
    )


@router.post(
    "/accept-draft/{draft_id}",
    response_model=AcceptDraftResponse,
    summary="Accept draft (Admin)",
    description="Accept and apply a draft update. Admin only."
)
async def accept_draft(
    draft_id: str,
    request: AcceptDraftRequest,
    x_user_email: str = Header(..., description="Admin email address")
) -> AcceptDraftResponse:
    """Accept and apply a draft update (admin only)."""
    workflow = get_workflow_service()

    try:
        result = await workflow.accept_draft(
            draft_id=draft_id,
            admin_email=x_user_email,
            apply_immediately=request.apply_immediately,
            commit_changes=request.commit_changes,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return AcceptDraftResponse(
        success=result.get("success", False),
        draft_id=draft_id,
        approved=result.get("approved", False),
        applied=result.get("applied", False),
        message=result.get("message", ""),
        git_commit_sha=result.get("git_commit"),
        pr_url=result.get("pr_url"),
    )


@router.post(
    "/reject-draft/{draft_id}",
    response_model=RejectDraftResponse,
    summary="Reject draft (Admin)",
    description="Reject a draft update. Admin only."
)
async def reject_draft(
    draft_id: str,
    request: RejectDraftRequest,
    x_user_email: str = Header(..., description="Admin email address")
) -> RejectDraftResponse:
    """Reject a draft update (admin only)."""
    workflow = get_workflow_service()

    try:
        result = await workflow.reject_draft(
            draft_id=draft_id,
            admin_email=x_user_email,
            reason=request.reason,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return RejectDraftResponse(
        success=result.get("success", False),
        draft_id=draft_id,
        message=result.get("message", ""),
    )


# ==================== Queue Management (Admin) ====================

@router.get(
    "/queue",
    response_model=QueueResponse,
    summary="Get pending question queue (Admin)",
    description="Get the queue of pending/escalated questions. Admin only."
)
async def get_queue(
    x_user_email: str = Header(..., description="Admin email address")
) -> QueueResponse:
    """Get pending question queue (admin only)."""
    permission = get_permission_service()

    if not permission.is_admin(x_user_email):
        raise HTTPException(
            status_code=403,
            detail="Only admins can view the question queue"
        )

    workflow = get_workflow_service()
    questions = workflow.get_pending_questions()

    items = [
        PendingQuestionItem(
            id=q.id,
            user_email=q.user_email,
            question=q.question,
            bot_answer=q.bot_answer,
            rejection_reason=q.rejection_reason,
            platform=q.platform,
            status=q.status,
            created_at=q.created_at,
        )
        for q in questions
    ]

    return QueueResponse(
        pending_questions=items,
        total_count=len(items),
    )


@router.post(
    "/queue/{question_id}/respond",
    response_model=QueueRespondResponse,
    summary="Respond to queued question (Admin)",
    description="Respond to a pending question. Admin only."
)
async def respond_to_question(
    question_id: str,
    request: QueueRespondRequest,
    x_user_email: str = Header(..., description="Admin email address")
) -> QueueRespondResponse:
    """Respond to a pending question (admin only)."""
    workflow = get_workflow_service()

    try:
        result = await workflow.respond_to_question(
            question_id=question_id,
            admin_email=x_user_email,
            response=request.response,
            action=request.action,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not result.get("success"):
        raise HTTPException(
            status_code=404,
            detail=result.get("error", "Question not found")
        )

    return QueueRespondResponse(
        success=True,
        question_id=question_id,
        action=result.get("action", request.action),
        message=result.get("message", "Response recorded"),
    )


# ==================== Git Sync (Admin) ====================

@router.post(
    "/git-sync",
    response_model=GitSyncResponse,
    summary="Sync changes to git (Admin)",
    description="Sync all documentation changes to git repository. Admin only."
)
async def git_sync(
    request: GitSyncRequest,
    x_user_email: str = Header(..., description="Admin email address")
) -> GitSyncResponse:
    """Sync changes to git (admin only)."""
    workflow = get_workflow_service()

    try:
        result = await workflow.git_sync(
            admin_email=x_user_email,
            commit_message=request.commit_message,
            branch_name=request.branch_name,
            create_pr=request.create_pr,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    return GitSyncResponse(
        success=result.get("success", False),
        branch=result.get("branch"),
        commit_sha=result.get("commit_sha"),
        pr_url=result.get("pr_url"),
        message=result.get("message", ""),
        error=result.get("error"),
    )


# ==================== Language Preference ====================

@router.post(
    "/set-language",
    response_model=SetLanguageResponse,
    summary="Set language preference",
    description="Set user's language preference for documentation."
)
async def set_language(
    request: SetLanguageRequest,
    x_user_email: str = Header(..., description="User email address")
) -> SetLanguageResponse:
    """Set user's language preference."""
    language_service = get_language_service()

    lang = language_service.parse_language(request.language)
    if not lang:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid language: {request.language}. Supported: en, hu"
        )

    language_service.set_user_preference(x_user_email, lang)

    return SetLanguageResponse(
        success=True,
        language=lang.value,
        message=f"Language set to {language_service.get_language_name(lang)}",
    )
