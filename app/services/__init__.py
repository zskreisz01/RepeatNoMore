"""Shared services for RepeatNoMore application."""

# Lazy imports to avoid loading heavy dependencies (sentence-transformers, etc.) on module load
# Import these directly when needed:
#   from app.services.qa_service import process_question, QAResult
#   from app.services.permission_service import get_permission_service
#   from app.services.language_service import get_language_service

__all__ = [
    "process_question",
    "QAResult",
    "get_permission_service",
    "get_language_service",
]


def __getattr__(name: str):
    """Lazy import attributes."""
    if name in ("process_question", "QAResult"):
        from app.services.qa_service import process_question, QAResult
        return {"process_question": process_question, "QAResult": QAResult}[name]
    elif name == "get_permission_service":
        from app.services.permission_service import get_permission_service
        return get_permission_service
    elif name == "get_language_service":
        from app.services.language_service import get_language_service
        return get_language_service
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
