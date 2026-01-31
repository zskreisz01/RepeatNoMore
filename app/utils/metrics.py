"""Metrics collection and monitoring for RepeatNoMore."""

import time
from typing import Dict, Any, Optional
from contextlib import contextmanager
from collections import defaultdict
from datetime import datetime

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Define Prometheus metrics
# Request metrics
REQUEST_COUNT = Counter(
    'repeatnomore_requests_total',
    'Total number of requests',
    ['endpoint', 'method', 'status']
)

REQUEST_DURATION = Histogram(
    'repeatnomore_request_duration_seconds',
    'Request duration in seconds',
    ['endpoint', 'method']
)

# RAG metrics
EMBEDDINGS_GENERATED = Counter(
    'repeatnomore_embeddings_generated_total',
    'Total number of embeddings generated'
)

DOCUMENTS_INDEXED = Counter(
    'repeatnomore_documents_indexed_total',
    'Total number of documents indexed'
)

QUERIES_PROCESSED = Counter(
    'repeatnomore_queries_processed_total',
    'Total number of queries processed',
    ['query_type']
)

QUERY_DURATION = Histogram(
    'repeatnomore_query_duration_seconds',
    'Query processing duration in seconds',
    ['query_type']
)

# Vector store metrics
VECTOR_STORE_SIZE = Gauge(
    'repeatnomore_vector_store_documents',
    'Number of documents in vector store'
)

RETRIEVAL_SCORES = Histogram(
    'repeatnomore_retrieval_scores',
    'Distribution of retrieval similarity scores'
)

# LLM metrics
LLM_REQUESTS = Counter(
    'repeatnomore_llm_requests_total',
    'Total number of LLM requests',
    ['model']
)

LLM_DURATION = Histogram(
    'repeatnomore_llm_duration_seconds',
    'LLM request duration in seconds',
    ['model'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float("inf"))
)

LLM_TOKENS = Counter(
    'repeatnomore_llm_tokens_total',
    'Total number of tokens processed',
    ['model', 'token_type']
)

LLM_TOKENS_PER_SECOND = Histogram(
    'repeatnomore_llm_tokens_per_second',
    'Token generation speed (tokens per second)',
    ['model'],
    buckets=(1, 5, 10, 20, 50, 100, 200, float("inf"))
)

# Retrieval metrics
RETRIEVAL_DURATION = Histogram(
    'repeatnomore_retrieval_duration_seconds',
    'Retrieval duration in seconds',
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, float("inf"))
)

# Agent metrics
AGENT_EXECUTIONS = Counter(
    'repeatnomore_agent_executions_total',
    'Total number of agent executions',
    ['agent_type', 'status']
)

AGENT_DURATION = Histogram(
    'repeatnomore_agent_duration_seconds',
    'Agent execution duration in seconds',
    ['agent_type']
)

# Error metrics
ERRORS_TOTAL = Counter(
    'repeatnomore_errors_total',
    'Total number of errors',
    ['error_type', 'component']
)


class MetricsCollector:
    """Collect and manage application metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.settings = get_settings()
        self.enabled = self.settings.prometheus_enabled
        self._start_time = time.time()
        self._custom_metrics: Dict[str, Any] = defaultdict(int)

        if self.enabled:
            logger.info("metrics_collector_initialized", enabled=True)
        else:
            logger.info("metrics_collector_disabled")

    @contextmanager
    def track_request(self, endpoint: str, method: str):
        """
        Context manager for tracking HTTP requests.

        Args:
            endpoint: API endpoint
            method: HTTP method

        Yields:
            Dict for storing request metadata
        """
        start_time = time.time()
        metadata = {"status": 200}

        try:
            yield metadata
        except Exception as e:
            metadata["status"] = 500
            logger.error("request_failed", endpoint=endpoint, error=str(e))
            raise
        finally:
            duration = time.time() - start_time
            status = metadata.get("status", 500)

            if self.enabled:
                REQUEST_COUNT.labels(
                    endpoint=endpoint,
                    method=method,
                    status=str(status)
                ).inc()

                REQUEST_DURATION.labels(
                    endpoint=endpoint,
                    method=method
                ).observe(duration)

            logger.info(
                "request_completed",
                endpoint=endpoint,
                method=method,
                status=status,
                duration=duration
            )

    @contextmanager
    def track_query(self, query_type: str):
        """
        Context manager for tracking query processing.

        Args:
            query_type: Type of query (e.g., 'qa', 'search')

        Yields:
            Dict for storing query metadata
        """
        start_time = time.time()
        metadata = {}

        try:
            yield metadata
        finally:
            duration = time.time() - start_time

            if self.enabled:
                QUERIES_PROCESSED.labels(query_type=query_type).inc()
                QUERY_DURATION.labels(query_type=query_type).observe(duration)

            logger.info(
                "query_processed",
                query_type=query_type,
                duration=duration
            )

    @contextmanager
    def track_agent(self, agent_type: str):
        """
        Context manager for tracking agent execution.

        Args:
            agent_type: Type of agent

        Yields:
            Dict for storing agent metadata
        """
        start_time = time.time()
        metadata = {"status": "completed"}

        try:
            yield metadata
        except Exception as e:
            metadata["status"] = "failed"
            logger.error("agent_execution_failed", agent_type=agent_type, error=str(e))
            raise
        finally:
            duration = time.time() - start_time
            status = metadata.get("status", "failed")

            if self.enabled:
                AGENT_EXECUTIONS.labels(
                    agent_type=agent_type,
                    status=status
                ).inc()

                AGENT_DURATION.labels(agent_type=agent_type).observe(duration)

            logger.info(
                "agent_execution_completed",
                agent_type=agent_type,
                status=status,
                duration=duration
            )

    def record_embeddings(self, count: int = 1):
        """Record embedding generation."""
        if self.enabled:
            EMBEDDINGS_GENERATED.inc(count)

    def record_documents_indexed(self, count: int):
        """Record documents indexed."""
        if self.enabled:
            DOCUMENTS_INDEXED.inc(count)

    def update_vector_store_size(self, size: int):
        """Update vector store size metric."""
        if self.enabled:
            VECTOR_STORE_SIZE.set(size)

    def record_retrieval_score(self, score: float):
        """Record a retrieval similarity score."""
        if self.enabled:
            RETRIEVAL_SCORES.observe(score)

    def record_llm_request(self, model: str, duration: float, tokens: Optional[Dict[str, int]] = None):
        """
        Record an LLM request.

        Args:
            model: Model name
            duration: Request duration in seconds
            tokens: Dict with 'prompt' and 'completion' token counts (optional)
        """
        if self.enabled:
            LLM_REQUESTS.labels(model=model).inc()
            LLM_DURATION.labels(model=model).observe(duration)

            if tokens:
                if 'prompt' in tokens:
                    LLM_TOKENS.labels(model=model, token_type='prompt').inc(tokens['prompt'])
                if 'completion' in tokens:
                    completion_tokens = tokens['completion']
                    LLM_TOKENS.labels(model=model, token_type='completion').inc(completion_tokens)

                    # Calculate and record tokens per second
                    if duration > 0 and completion_tokens > 0:
                        tokens_per_second = completion_tokens / duration
                        LLM_TOKENS_PER_SECOND.labels(model=model).observe(tokens_per_second)

        # Log the request details
        logger.info(
            "llm_request_recorded",
            model=model,
            duration=round(duration, 3),
            prompt_tokens=tokens.get("prompt") if tokens else None,
            completion_tokens=tokens.get("completion") if tokens else None,
            tokens_per_second=round(tokens["completion"] / duration, 2) if tokens and duration > 0 and tokens.get("completion") else None
        )

    def record_retrieval_time(self, duration: float):
        """
        Record retrieval operation duration.

        Args:
            duration: Retrieval duration in seconds
        """
        if self.enabled:
            RETRIEVAL_DURATION.observe(duration)

    def record_error(self, error_type: str, component: str):
        """
        Record an error occurrence.

        Args:
            error_type: Type of error
            component: Component where error occurred
        """
        if self.enabled:
            ERRORS_TOTAL.labels(
                error_type=error_type,
                component=component
            ).inc()

        logger.error(
            "error_recorded",
            error_type=error_type,
            component=component
        )

    def get_custom_metric(self, name: str) -> Any:
        """Get a custom metric value."""
        return self._custom_metrics.get(name, 0)

    def increment_custom_metric(self, name: str, value: int = 1):
        """Increment a custom metric."""
        self._custom_metrics[name] += value

    def get_uptime(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self._start_time

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of key metrics.

        Returns:
            Dict with metrics summary
        """
        return {
            "uptime_seconds": self.get_uptime(),
            "uptime_formatted": self._format_uptime(self.get_uptime()),
            "timestamp": datetime.utcnow().isoformat(),
            "enabled": self.enabled,
            "custom_metrics": dict(self._custom_metrics)
        }

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Format uptime in human-readable format."""
        days, remainder = divmod(int(seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")

        return " ".join(parts)

    def export_metrics(self) -> bytes:
        """
        Export metrics in Prometheus format.

        Returns:
            bytes: Prometheus-formatted metrics
        """
        if not self.enabled:
            return b""

        return generate_latest()


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """
    Get or create global metrics collector.

    Returns:
        MetricsCollector: The metrics collector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# Convenience decorators
def track_time(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """
    Decorator to track execution time of a function.

    Args:
        metric_name: Name for the metric
        labels: Optional labels for the metric

    Returns:
        Decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                logger.info(
                    f"{metric_name}_duration",
                    function=func.__name__,
                    duration=duration,
                    **(labels or {})
                )
        return wrapper
    return decorator
