"""Question-answering agent using RAG and LLM."""

import time
from typing import Any, Dict, Optional

from app.config import get_settings
from app.llm import BaseLLMProvider, LLMMessage, LLMOptions, get_llm_provider
from app.rag.retriever import get_retriever
from app.utils.logging import get_logger
from app.utils.metrics import get_metrics_collector

logger = get_logger(__name__)


class QAAgent:
    """Question answering agent with RAG."""

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        """
        Initialize the QA agent.

        Args:
            llm_provider: Optional LLM provider instance. If not provided,
                         the default provider from settings will be used.
        """
        self.settings = get_settings()
        self.retriever = get_retriever()
        self.metrics = get_metrics_collector()
        self.system_prompt = self._build_system_prompt()

        # Use injected provider or get default from settings
        self._llm = llm_provider or get_llm_provider()

        logger.info(
            "QA Agent initialized",
            provider=self._llm.provider_name,
            model=self._llm.model_name,
        )

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for the LLM.

        Returns:
            str: System prompt
        """
        return """You are RepeatNoMore, an AI assistant specialized in helping developers with framework questions and technical support.

Your role is to:
1. Answer questions accurately based on the provided documentation context
2. Provide code examples when relevant
3. Be concise but thorough
4. Cite sources when possible
5. Admit when you don't have enough information to answer

Guidelines:
- Use the context provided from the documentation to answer questions
- If the context doesn't contain relevant information, say so honestly
- Format code snippets using markdown code blocks
- Be helpful and professional
- Focus on practical, actionable advice

When answering:
- Start with a direct answer
- Provide relevant details and examples
- Mention the source documentation if applicable
- Suggest related topics when helpful
"""

    def _format_context(self, context: str, sources: list) -> str:
        """
        Format retrieved context for the prompt.

        Args:
            context: Retrieved context string
            sources: List of source documents

        Returns:
            str: Formatted context
        """
        formatted = "# Documentation Context\n\n"
        formatted += context
        formatted += "\n\n# Sources\n"

        for i, source in enumerate(sources, 1):
            source_file = source.get("metadata", {}).get("source", "Unknown")
            formatted += f"{i}. {source_file}\n"

        return formatted

    def _build_prompt(self, question: str, context: str) -> str:
        """
        Build the full prompt for the LLM.

        Args:
            question: User's question
            context: Retrieved context

        Returns:
            str: Complete prompt
        """
        return f"""{context}

# Question
{question}

# Instructions
Answer the question based on the documentation context provided above. Be accurate, helpful, and concise.
If the context doesn't contain enough information to fully answer the question, acknowledge this limitation.
"""

    def answer(
        self,
        question: str,
        top_k: Optional[int] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG.

        Args:
            question: Question to answer
            top_k: Number of documents to retrieve
            temperature: LLM temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Dict containing:
                - answer: Generated answer
                - sources: Source documents
                - confidence: Confidence score
                - processing_time: Time taken

        Raises:
            ValueError: If question is invalid
            RuntimeError: If generation fails
        """
        start_time = time.time()

        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        logger.info("answering_question", question=question[:100])

        try:
            # Step 1: Retrieve relevant documents
            logger.info("retrieving_documents")
            retrieval_start_time = time.time()
            retrieval_result = self.retriever.retrieve_with_context(
                query=question,
                top_k=top_k
            )
            retrieval_duration = time.time() - retrieval_start_time

            context_str = retrieval_result["context"]
            sources = retrieval_result["sources"]
            num_docs = retrieval_result["num_documents"]

            # Record retrieval metrics
            self.metrics.record_retrieval_time(retrieval_duration)
            logger.info("documents_retrieved", count=num_docs, retrieval_duration=retrieval_duration)

            # Step 2: Format context
            formatted_context = self._format_context(context_str, sources)

            # Step 3: Build prompt
            prompt = self._build_prompt(question, formatted_context)

            # Step 4: Generate answer with LLM abstraction
            logger.info(
                "generating_answer",
                provider=self._llm.provider_name,
                model=self._llm.model_name,
            )

            llm_start_time = time.time()

            messages = [
                LLMMessage(role="system", content=self.system_prompt),
                LLMMessage(role="user", content=prompt),
            ]
            options = LLMOptions(
                temperature=temperature,
                max_tokens=max_tokens,
            )

            response = self._llm.chat(messages, options)
            llm_duration = time.time() - llm_start_time

            answer = response.content

            # Extract token counts from response
            tokens = None
            if response.tokens:
                tokens = {
                    "prompt": response.tokens.prompt_tokens,
                    "completion": response.tokens.completion_tokens,
                }

            # Record LLM metrics
            self.metrics.record_llm_request(
                model=self._llm.model_name,
                duration=llm_duration,
                tokens=tokens,
            )

            logger.info(
                "llm_response_generated",
                provider=self._llm.provider_name,
                model=self._llm.model_name,
                llm_duration=llm_duration,
                prompt_tokens=tokens.get("prompt") if tokens else None,
                completion_tokens=tokens.get("completion") if tokens else None,
            )

            # Step 5: Calculate confidence based on retrieval scores
            if sources:
                avg_score = sum(s["score"] for s in sources) / len(sources)
                confidence = min(0.95, avg_score)  # Cap at 0.95
            else:
                confidence = 0.3  # Low confidence if no sources

            processing_time = time.time() - start_time

            # Calculate retrieval time (total time minus LLM time)
            retrieval_time = processing_time - llm_duration

            logger.info(
                "answer_generated",
                processing_time=processing_time,
                llm_duration=llm_duration,
                retrieval_time=retrieval_time,
                confidence=confidence,
                sources_used=len(sources),
                provider=self._llm.provider_name,
                model=self._llm.model_name,
            )

            return {
                "answer": answer,
                "sources": sources,
                "confidence": confidence,
                "processing_time": processing_time,
                "llm_duration": llm_duration,
                "retrieval_time": retrieval_time,
                "model": self._llm.model_name,
                "provider": self._llm.provider_name,
                "tokens": tokens,
            }

        except Exception as e:
            logger.error("answer_generation_failed", error=str(e))
            raise RuntimeError(f"Failed to generate answer: {e}")

    def stream_answer(self, question: str, **kwargs):
        """
        Stream answer generation (for future implementation).

        Args:
            question: Question to answer
            **kwargs: Additional parameters

        Yields:
            str: Answer chunks
        """
        # TODO: Implement streaming response
        raise NotImplementedError("Streaming not yet implemented")


# Global instance
_qa_agent: Optional[QAAgent] = None


def get_qa_agent() -> QAAgent:
    """
    Get or create a global QA agent instance.

    Returns:
        QAAgent: The QA agent
    """
    global _qa_agent
    if _qa_agent is None:
        _qa_agent = QAAgent()
    return _qa_agent
