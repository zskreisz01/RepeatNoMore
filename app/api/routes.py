"""API routes for RepeatNoMore."""

import time
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from app.api.schemas import (
    QuestionRequest,
    QuestionResponse,
    DocumentIndexRequest,
    DocumentIndexResponse,
    HealthResponse,
    FeedbackRequest,
    FeedbackResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    Source,
    ErrorResponse,
    BudgetStatusResponse,
)
from app.rag.vector_store import get_vector_store
from app.services.qa_service import process_question
from app.services.budget_service import get_budget_service
from app.rag.document_loader import get_document_loader
from app.config import get_settings
from app.llm import get_llm_provider
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Cache for Azure Bot Framework access token
_bot_token_cache: dict[str, Any] = {"token": None, "expires_at": 0}


async def _get_bot_access_token() -> str:
    """
    Get an access token for Azure Bot Framework.

    Returns:
        str: Access token for authenticating with Bot Framework

    Raises:
        Exception: If token acquisition fails
    """
    import time as time_module

    settings = get_settings()

    # Check if we have a valid cached token
    if _bot_token_cache["token"] and time_module.time() < _bot_token_cache["expires_at"] - 60:
        return _bot_token_cache["token"]

    # For multi-tenant bots, use the common endpoint
    # For single-tenant bots, use the specific tenant ID
    if settings.azure_ad_tenant_id:
        token_url = f"https://login.microsoftonline.com/{settings.azure_ad_tenant_id}/oauth2/v2.0/token"
    else:
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"

    # IMPORTANT: The client_id for the token MUST match the Bot's Microsoft App ID
    # The token and the bot identity must be from the same App Registration
    bot_app_id = settings.azure_ad_client_id
    client_secret = settings.azure_ad_client_secret

    logger.info("requesting_bot_token", app_id=bot_app_id, token_url=token_url)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": bot_app_id,
                "client_secret": client_secret,
                "scope": "https://api.botframework.com/.default",
            },
        )

        if response.status_code != 200:
            logger.error("bot_token_acquisition_failed", status=response.status_code, body=response.text)
            raise Exception(f"Failed to get bot token: {response.text}")

        token_data = response.json()
        _bot_token_cache["token"] = token_data["access_token"]
        _bot_token_cache["expires_at"] = time_module.time() + token_data.get("expires_in", 3600)

        return _bot_token_cache["token"]


async def _send_bot_reply(
    service_url: str,
    conversation_id: str,
    activity_id: str,
    message: str,
    recipient: dict[str, Any],
) -> None:
    """
    Send a reply message back to Azure Bot Framework.

    Args:
        service_url: The serviceUrl from the incoming activity
        conversation_id: The conversation ID
        activity_id: The activity ID to reply to
        message: The message text to send
        recipient: The original sender (user) who will receive the reply
    """
    print("Sending bot reply:", message)
    settings = get_settings()
    token = await _get_bot_access_token()

    reply_url = f"{service_url}v3/conversations/{conversation_id}/activities/{activity_id}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            reply_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "type": "message",
                "text": message,
                "from": {
                    "id": settings.app_name,
                    "name": "RepeatNoMore",
                },
                "recipient": recipient,
                "conversation": {"id": conversation_id},
                "replyToId": activity_id,
            },
            timeout=30.0,
        )

        if response.status_code not in (200, 201):
            logger.error(
                "bot_reply_failed",
                status=response.status_code,
                body=response.text,
                url=reply_url,
                from_id=settings.microsoft_app_id,
                recipient=recipient,
            )
        else:
            logger.info("bot_reply_sent", conversation_id=conversation_id)
    print("Bot reply sent.")


async def _process_teams_message(body: dict[str, Any]) -> None:
    """
    Process a Teams message in the background and send reply.

    Args:
        body: The incoming activity body from Bot Framework
    """
    text = body.get("text", "").strip()
    service_url = body.get("serviceUrl", "")
    conversation_id = body.get("conversation", {}).get("id", "")
    activity_id = body.get("id", "")
    # The original sender becomes the recipient of our reply
    recipient = body.get("from", {})

    try:
        result = process_question(text, source="teams")
        answer = result.answer if result.answer else "No answer generated"
        logger.info("teams_answer_generated", answer_preview=answer[:100])
    except Exception as e:
        logger.error("teams_question_processing_failed", error=str(e))
        answer = f"Sorry, I encountered an error processing your question: {str(e)}"

    await _send_bot_reply(service_url, conversation_id, activity_id, answer, recipient)


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse: Service health status
    """
    settings = get_settings()

    # Check components
    components = {}

    # Check vector store
    try:
        store = get_vector_store()
        doc_count = store.count()
        components["vector_store"] = f"healthy ({doc_count} docs)"
    except Exception as e:
        logger.error("vector_store_health_check_failed", error=str(e))
        components["vector_store"] = f"unhealthy: {str(e)}"

    # Check LLM provider
    try:
        llm_provider = get_llm_provider()
        if llm_provider.is_available():
            components["llm"] = f"healthy ({llm_provider.provider_name}: {llm_provider.model_name})"
        else:
            components["llm"] = f"unavailable ({llm_provider.provider_name})"
    except Exception as e:
        logger.error("llm_health_check_failed", error=str(e))
        components["llm"] = f"unhealthy: {str(e)}"

    # Determine overall status
    status_val = "healthy" if all(v.startswith("healthy") for v in components.values()) else "degraded"

    return HealthResponse(
        status=status_val,
        version="0.1.0",
        components=components,
        timestamp=datetime.utcnow().isoformat()
    )


@router.get("/budget-status", response_model=BudgetStatusResponse)
async def get_budget_status() -> BudgetStatusResponse:
    """
    Get current budget status.

    Returns:
        BudgetStatusResponse: Current budget status including usage and limits
    """
    logger.info("budget_status_requested")

    budget_service = get_budget_service()
    status = budget_service.get_status()

    return BudgetStatusResponse(
        total_budget=status.total_budget,
        used_amount=status.used_amount,
        remaining=status.remaining,
        percentage_used=status.percentage_used,
        requests_used=status.requests_used,
        service_active=status.service_active,
        current_month=status.current_month,
        last_updated=status.last_updated,
        estimated_cost_per_request=status.estimated_cost_per_request,
    )


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest) -> QuestionResponse:
    """
    Ask a question and get an answer using RAG.

    Args:
        request: Question request

    Returns:
        QuestionResponse: Generated answer with sources

    Raises:
        HTTPException: If question processing fails
    """
    logger.info("question_received", question=request.question[:100])

    try:
        result = process_question(
            request.question,
            top_k=request.top_k or 5,
            source="api"
        )

        # Format sources
        sources = []
        if request.include_sources:
            for src in result.sources:
                sources.append(Source(
                    doc_id=src["doc_id"],
                    content=src["document"][:500],  # Truncate for response
                    source=src["metadata"].get("source", "Unknown"),
                    score=src["score"]
                ))

        response = QuestionResponse(
            answer=result.answer,
            sources=sources,
            confidence=result.confidence,
            processing_time=result.processing_time
        )

        logger.info(
            "question_answered",
            processing_time=result.processing_time,
            llm_duration=result.llm_duration,
            retrieval_time=result.retrieval_time,
            model=result.model,
            confidence=result.confidence,
            sources_count=len(sources)
        )

        return response

    except ValueError as e:
        logger.error("invalid_question", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("question_processing_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process question: {str(e)}"
        )


@router.post("/index", response_model=DocumentIndexResponse)
async def index_documents(request: DocumentIndexRequest) -> DocumentIndexResponse:
    """
    Index documents into the vector store.

    Args:
        request: Document indexing request

    Returns:
        DocumentIndexResponse: Indexing results

    Raises:
        HTTPException: If indexing fails
    """
    start_time = time.time()
    logger.info("indexing_requested", request=request.dict())

    try:
        loader = get_document_loader()
        store = get_vector_store(reset=request.reset)

        documents = []
        errors = []

        # Load documents based on request type
        if request.text:
            logger.info("indexing_text")
            docs = loader.load_text(request.text, metadata=request.metadata)
            documents.extend(docs)

        elif request.file_path:
            logger.info("indexing_file", file_path=request.file_path)
            try:
                docs = loader.load_file(request.file_path)
                documents.extend(docs)
            except Exception as e:
                errors.append(f"Failed to load {request.file_path}: {str(e)}")

        elif request.directory_path:
            logger.info("indexing_directory", directory_path=request.directory_path)
            try:
                docs = loader.load_directory(request.directory_path)
                documents.extend(docs)
            except Exception as e:
                errors.append(f"Failed to load directory: {str(e)}")

        else:
            # Index default knowledge base
            settings = get_settings()
            logger.info("indexing_knowledge_base", path=settings.docs_repo_path)
            try:
                docs = loader.load_directory(
                    settings.docs_repo_path,
                    glob_pattern="**/*.md"
                )
                documents.extend(docs)
            except Exception as e:
                errors.append(f"Failed to load knowledge base: {str(e)}")

        # Add documents to vector store
        if documents:
            logger.info("adding_to_vector_store", count=len(documents))

            texts = [doc.content for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            ids = [doc.doc_id for doc in documents]

            store.add_documents(texts, metadatas, ids)

        processing_time = time.time() - start_time

        response = DocumentIndexResponse(
            success=len(documents) > 0,
            documents_indexed=len(set(doc.metadata.get("source", "") for doc in documents)),
            chunks_created=len(documents),
            processing_time=processing_time,
            errors=errors
        )

        logger.info(
            "indexing_completed",
            documents_indexed=response.documents_indexed,
            chunks_created=response.chunks_created,
            processing_time=processing_time
        )

        return response

    except Exception as e:
        logger.error("indexing_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index documents: {str(e)}"
        )


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest) -> SearchResponse:
    """
    Search for documents in the vector store.

    Args:
        request: Search request

    Returns:
        SearchResponse: Search results

    Raises:
        HTTPException: If search fails
    """
    start_time = time.time()
    logger.info("search_requested", query=request.query[:100])

    try:
        store = get_vector_store()

        # Query vector store
        results = store.query(
            query_text=request.query,
            n_results=request.top_k,
            where=request.metadata_filter,
            min_score=request.min_score
        )

        # Format results
        search_results = []
        for i in range(len(results["ids"][0])):
            search_results.append(SearchResult(
                doc_id=results["ids"][0][i],
                content=results["documents"][0][i],
                metadata=results["metadatas"][0][i],
                score=1 - (results["distances"][0][i] / 2)
            ))

        processing_time = time.time() - start_time

        response = SearchResponse(
            results=search_results,
            total_results=len(search_results),
            query=request.query,
            processing_time=processing_time
        )

        logger.info(
            "search_completed",
            results_count=len(search_results),
            processing_time=processing_time
        )

        return response

    except Exception as e:
        logger.error("search_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """
    Submit feedback for an answer.

    Args:
        request: Feedback request

    Returns:
        FeedbackResponse: Feedback confirmation

    Note:
        Currently logs feedback. Future: Store in database for analysis.
    """
    logger.info(
        "feedback_received",
        rating=request.rating,
        has_comment=bool(request.comment),
        session_id=request.session_id
    )

    # TODO: Store feedback in database
    # For now, just log it
    feedback_id = f"fb_{int(time.time())}"

    return FeedbackResponse(
        success=True,
        feedback_id=feedback_id,
        message="Thank you for your feedback!"
    )


@router.post("/webhook")
async def teams_webhook(request: Request, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """
    Receive messages from Teams via Azure Bot Service.

    The Bot Framework expects:
    1. Immediate HTTP 200 response to acknowledge receipt
    2. Reply sent back via the Bot Framework REST API to serviceUrl

    This endpoint processes messages in the background and sends replies
    asynchronously to avoid timeout issues with long-running LLM calls.
    """
    try:
        body = await request.json()
        logger.info("teams_message_received", activity_type=body.get("type"))

        activity_type = body.get("type")

        if activity_type == "message":
            text = body.get("text", "").strip()
            if not text:
                return {"status": "no text"}

            logger.info("teams_user_question", question=text)

            # Process in background and send reply via Bot Framework API
            background_tasks.add_task(_process_teams_message, body)

            # Return 200 immediately to acknowledge receipt
            return {"status": "accepted"}

        elif activity_type == "conversationUpdate":
            logger.info("teams_conversation_update")
            return {"status": "ok"}

        elif activity_type == "typing":
            # User is typing - no action needed
            return {"status": "ok"}

        else:
            logger.info("teams_unhandled_activity", activity_type=activity_type)
            return {"status": "ok"}

    except Exception as e:
        logger.error("teams_webhook_error", error=str(e))
        return {"status": "error", "message": str(e)}
