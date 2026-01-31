"""Shared QA service for multi-platform question answering.

This module provides the core question-answering logic used by all integrations:
- REST API (/ask endpoint)
- Teams webhook
- Discord bot
"""

from dataclasses import dataclass
from typing import Any

from app.agents.qa_agent import get_qa_agent
from app.config import get_settings
from app.services.budget_service import get_budget_service
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class QAResult:
    """Structured result from QA processing."""

    answer: str
    sources: list[dict[str, Any]]
    confidence: float
    processing_time: float
    llm_duration: float
    retrieval_time: float
    model: str
    tokens: dict[str, int] | None = None


def process_question(
    question: str,
    top_k: int = 5,
    source: str = "unknown",
) -> QAResult:
    """
    Process a question using the QA agent.

    This is the core question-answering logic shared across all integrations.

    Args:
        question: The question to answer
        top_k: Number of top documents to retrieve
        source: Source of the question (api, discord, teams) for logging

    Returns:
        QAResult containing answer, sources, confidence, and metrics

    Raises:
        ValueError: If the question is invalid
        RuntimeError: If question processing fails or budget exceeded
    """
    settings = get_settings()

    # Check budget before processing (if budget tracking is enabled)
    if settings.budget_enabled:
        budget_service = get_budget_service()
        if not budget_service.is_service_active():
            logger.warning("budget_exceeded", source=source)
            raise RuntimeError(
                "Service temporarily unavailable: Monthly budget limit reached. "
                "Service will resume at the start of next month."
            )

    logger.info(
        "processing_question",
        question=question[:100],
        source=source,
        top_k=top_k,
    )

    qa_agent = get_qa_agent()
    result = qa_agent.answer(question=question, top_k=top_k)

    # Record the request for budget tracking (after successful processing)
    if settings.budget_enabled:
        budget_service = get_budget_service()
        budget_service.record_request(request_type="llm")

    logger.info(
        "question_processed",
        source=source,
        processing_time=result["processing_time"],
        confidence=result["confidence"],
        sources_count=len(result["sources"]),
    )

    return QAResult(
        answer=result["answer"],
        sources=result["sources"],
        confidence=result["confidence"],
        processing_time=result["processing_time"],
        llm_duration=result["llm_duration"],
        retrieval_time=result["retrieval_time"],
        model=result["model"],
        tokens=result.get("tokens"),
    )
