"""API request and response schemas."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# Question Answering Schemas
class QuestionRequest(BaseModel):
    """Request schema for asking questions."""

    question: str = Field(..., description="The question to ask", min_length=1, max_length=1000)
    top_k: Optional[int] = Field(default=None, description="Number of documents to retrieve", ge=1, le=20)
    include_sources: bool = Field(default=True, description="Include source documents in response")
    session_id: Optional[str] = Field(default=None, description="Session ID for conversation context")


class Source(BaseModel):
    """Source document information."""

    doc_id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Document content")
    source: str = Field(..., description="Source file path")
    score: float = Field(..., description="Relevance score", ge=0, le=1)


class QuestionResponse(BaseModel):
    """Response schema for questions."""

    answer: str = Field(..., description="Generated answer")
    sources: List[Source] = Field(default=[], description="Source documents used")
    confidence: float = Field(..., description="Confidence score", ge=0, le=1)
    processing_time: float = Field(..., description="Processing time in seconds")


# Document Indexing Schemas
class DocumentIndexRequest(BaseModel):
    """Request schema for indexing documents."""

    text: Optional[str] = Field(default=None, description="Text content to index")
    file_path: Optional[str] = Field(default=None, description="File path to index")
    directory_path: Optional[str] = Field(default=None, description="Directory to index recursively")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    reset: bool = Field(default=False, description="Reset collection before indexing")


class DocumentIndexResponse(BaseModel):
    """Response schema for document indexing."""

    success: bool = Field(..., description="Whether indexing was successful")
    documents_indexed: int = Field(..., description="Number of documents indexed")
    chunks_created: int = Field(..., description="Number of chunks created")
    processing_time: float = Field(..., description="Processing time in seconds")
    errors: List[str] = Field(default=[], description="Any errors encountered")


# Health Check Schema
class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    components: Dict[str, str] = Field(..., description="Component statuses")
    timestamp: str = Field(..., description="Current timestamp")


# Feedback Schema
class FeedbackRequest(BaseModel):
    """Feedback submission schema."""

    question: str = Field(..., description="Original question")
    answer: str = Field(..., description="Answer provided")
    rating: int = Field(..., description="Rating (1-5)", ge=1, le=5)
    comment: Optional[str] = Field(default=None, description="Additional feedback")
    session_id: Optional[str] = Field(default=None, description="Session ID")


class FeedbackResponse(BaseModel):
    """Feedback response schema."""

    success: bool = Field(..., description="Whether feedback was recorded")
    feedback_id: str = Field(..., description="Feedback ID")
    message: str = Field(..., description="Response message")


# Search Schema
class SearchRequest(BaseModel):
    """Document search request."""

    query: str = Field(..., description="Search query", min_length=1)
    top_k: int = Field(default=5, description="Number of results", ge=1, le=20)
    min_score: Optional[float] = Field(default=None, description="Minimum similarity score", ge=0, le=1)
    metadata_filter: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters")


class SearchResult(BaseModel):
    """Single search result."""

    doc_id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Document content")
    metadata: Dict[str, Any] = Field(..., description="Document metadata")
    score: float = Field(..., description="Similarity score")


class SearchResponse(BaseModel):
    """Search response schema."""

    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results")
    query: str = Field(..., description="Original query")
    processing_time: float = Field(..., description="Processing time in seconds")


# Error Response Schema
class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")


# ==================== Workflow Schemas ====================

# Q&A Workflow
class QAAcceptRequest(BaseModel):
    """Request to accept a Q&A answer and save to docs."""

    question: str = Field(..., description="The question", min_length=1)
    answer: str = Field(..., description="The accepted answer", min_length=1)
    language: str = Field(default="en", description="Language code (en/hu)")
    sources: Optional[List[str]] = Field(default=None, description="Source references")


class QAAcceptResponse(BaseModel):
    """Response for Q&A acceptance."""

    success: bool = Field(..., description="Whether the Q&A was saved")
    qa_id: Optional[str] = Field(default=None, description="Q&A ID")
    message: str = Field(..., description="Response message")
    file_path: Optional[str] = Field(default=None, description="File where Q&A was saved")


class QARejectRequest(BaseModel):
    """Request to reject a Q&A answer and escalate."""

    question: str = Field(..., description="The question", min_length=1)
    answer: str = Field(..., description="The bot's answer", min_length=1)
    reason: Optional[str] = Field(default=None, description="Rejection reason")
    platform: str = Field(default="api", description="Platform origin")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID")
    language: str = Field(default="en", description="Language code")


class QARejectResponse(BaseModel):
    """Response for Q&A rejection."""

    success: bool = Field(..., description="Whether the question was escalated")
    question_id: Optional[str] = Field(default=None, description="Question ID in queue")
    message: str = Field(..., description="Response message")


# Edit Docs Workflow
class EditDocsRequest(BaseModel):
    """Request to edit documentation (admin only)."""

    instruction: str = Field(..., description="Natural language edit instruction", min_length=1)
    target_file: Optional[str] = Field(default=None, description="Target file to edit")
    language: str = Field(default="en", description="Language code")
    commit_changes: bool = Field(default=True, description="Whether to commit to git")


class EditDocsResponse(BaseModel):
    """Response for edit docs request."""

    success: bool = Field(..., description="Whether the edit was processed")
    message: str = Field(..., description="Response message")
    changes_made: Optional[List[str]] = Field(default=None, description="List of changes made")
    files_modified: Optional[List[str]] = Field(default=None, description="Files modified")
    git_commit_sha: Optional[str] = Field(default=None, description="Git commit SHA")


# Feature Suggestion Workflow
class FeatureSuggestionRequest(BaseModel):
    """Request to submit a feature suggestion."""

    title: str = Field(..., description="Feature title", min_length=1, max_length=200)
    description: str = Field(..., description="Feature description", min_length=10)
    language: str = Field(default="en", description="Language code")


class FeatureSuggestionResponse(BaseModel):
    """Response for feature suggestion."""

    success: bool = Field(..., description="Whether suggestion was saved")
    feature_id: Optional[str] = Field(default=None, description="Feature ID")
    message: str = Field(..., description="Response message")


class FeatureSuggestionItem(BaseModel):
    """Feature suggestion item."""

    id: str = Field(..., description="Feature ID")
    title: str = Field(..., description="Feature title")
    description: str = Field(..., description="Feature description")
    user_email: str = Field(..., description="Submitter email")
    language: str = Field(..., description="Language")
    status: str = Field(..., description="Status")
    votes: int = Field(..., description="Vote count")
    created_at: str = Field(..., description="Creation timestamp")


class FeatureListResponse(BaseModel):
    """Response for listing features."""

    features: List[FeatureSuggestionItem] = Field(..., description="Feature list")
    total_count: int = Field(..., description="Total count")


# Draft Update Workflow
class DraftUpdateRequest(BaseModel):
    """Request to create a draft documentation update."""

    content: str = Field(..., description="Draft content", min_length=1)
    target_section: str = Field(..., description="Target documentation section", min_length=1)
    description: Optional[str] = Field(default=None, description="Change description")
    language: str = Field(default="en", description="Language code")


class DraftUpdateResponse(BaseModel):
    """Response for draft update creation."""

    success: bool = Field(..., description="Whether draft was created")
    draft_id: Optional[str] = Field(default=None, description="Draft ID")
    message: str = Field(..., description="Response message")


class DraftItem(BaseModel):
    """Draft update item."""

    id: str = Field(..., description="Draft ID")
    user_email: str = Field(..., description="Submitter email")
    content: str = Field(..., description="Draft content (truncated)")
    target_section: str = Field(..., description="Target section")
    description: str = Field(..., description="Description")
    language: str = Field(..., description="Language")
    status: str = Field(..., description="Status")
    created_at: str = Field(..., description="Creation timestamp")


class DraftListResponse(BaseModel):
    """Response for listing drafts."""

    drafts: List[DraftItem] = Field(..., description="Draft list")
    total_count: int = Field(..., description="Total count")
    pending_count: int = Field(..., description="Pending count")


class AcceptDraftRequest(BaseModel):
    """Request to accept a draft (admin only)."""

    apply_immediately: bool = Field(default=True, description="Apply draft immediately")
    commit_changes: bool = Field(default=True, description="Commit to git")


class AcceptDraftResponse(BaseModel):
    """Response for accepting a draft."""

    success: bool = Field(..., description="Whether draft was accepted")
    draft_id: str = Field(..., description="Draft ID")
    approved: bool = Field(..., description="Whether approved")
    applied: bool = Field(..., description="Whether applied")
    message: str = Field(..., description="Response message")
    git_commit_sha: Optional[str] = Field(default=None, description="Git commit SHA")
    pr_url: Optional[str] = Field(default=None, description="Pull request URL")


class RejectDraftRequest(BaseModel):
    """Request to reject a draft (admin only)."""

    reason: str = Field(..., description="Rejection reason", min_length=1)


class RejectDraftResponse(BaseModel):
    """Response for rejecting a draft."""

    success: bool = Field(..., description="Whether draft was rejected")
    draft_id: str = Field(..., description="Draft ID")
    message: str = Field(..., description="Response message")


# Queue Management
class PendingQuestionItem(BaseModel):
    """Pending question item."""

    id: str = Field(..., description="Question ID")
    user_email: str = Field(..., description="User email")
    question: str = Field(..., description="Question")
    bot_answer: str = Field(..., description="Bot's answer")
    rejection_reason: Optional[str] = Field(default=None, description="Rejection reason")
    platform: str = Field(..., description="Platform")
    status: str = Field(..., description="Status")
    created_at: str = Field(..., description="Creation timestamp")


class QueueResponse(BaseModel):
    """Response for question queue."""

    pending_questions: List[PendingQuestionItem] = Field(..., description="Pending questions")
    total_count: int = Field(..., description="Total count")


class QueueRespondRequest(BaseModel):
    """Request to respond to a queued question (admin only)."""

    response: str = Field(..., description="Admin response", min_length=1)
    action: str = Field(default="answer", description="Action: answer, on_hold, close")


class QueueRespondResponse(BaseModel):
    """Response for queue respond."""

    success: bool = Field(..., description="Whether response was recorded")
    question_id: str = Field(..., description="Question ID")
    action: str = Field(..., description="Action taken")
    message: str = Field(..., description="Response message")


# Git Sync
class GitSyncRequest(BaseModel):
    """Request to sync changes to git (admin only)."""

    commit_message: Optional[str] = Field(default=None, description="Custom commit message")
    branch_name: Optional[str] = Field(default=None, description="Branch name")
    create_pr: bool = Field(default=True, description="Create pull request")


class GitSyncResponse(BaseModel):
    """Response for git sync."""

    success: bool = Field(..., description="Whether sync was successful")
    branch: Optional[str] = Field(default=None, description="Branch name")
    commit_sha: Optional[str] = Field(default=None, description="Commit SHA")
    pr_url: Optional[str] = Field(default=None, description="Pull request URL")
    message: str = Field(..., description="Response message")
    error: Optional[str] = Field(default=None, description="Error message if failed")


# Language Preference
class SetLanguageRequest(BaseModel):
    """Request to set language preference."""

    language: str = Field(..., description="Language code (en/hu)")


class SetLanguageResponse(BaseModel):
    """Response for setting language."""

    success: bool = Field(..., description="Whether preference was set")
    language: str = Field(..., description="Set language")
    message: str = Field(..., description="Response message")


# ==================== Budget Schemas ====================


class BudgetStatusResponse(BaseModel):
    """Budget status response schema."""

    total_budget: float = Field(..., description="Monthly budget limit in USD")
    used_amount: float = Field(..., description="Estimated amount used this month in USD")
    remaining: float = Field(..., description="Remaining budget in USD")
    percentage_used: float = Field(
        ..., description="Percentage of budget used", ge=0, le=100
    )
    requests_used: int = Field(..., description="Number of requests this month", ge=0)
    service_active: bool = Field(..., description="Whether the service is active")
    current_month: str = Field(..., description="Current billing month (YYYY-MM)")
    last_updated: str = Field(..., description="Last update timestamp (ISO format)")
    estimated_cost_per_request: float = Field(
        ..., description="Estimated cost per LLM request in USD"
    )
