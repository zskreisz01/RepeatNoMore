"""Document retrieval for RAG system."""

from typing import List, Dict, Any, Optional
import logging

from app.config import get_settings
from app.rag.vector_store import get_vector_store, VectorStore

logger = logging.getLogger(__name__)


class RetrievalResult:
    """Represents a retrieved document with score."""

    def __init__(
        self, document: str, metadata: Dict[str, Any], score: float, doc_id: str
    ):
        """
        Initialize retrieval result.

        Args:
            document: Document text
            metadata: Document metadata
            score: Similarity score (0-1, higher is better)
            doc_id: Document ID
        """
        self.document = document
        self.metadata = metadata
        self.score = score
        self.doc_id = doc_id

    def __repr__(self) -> str:
        """String representation."""
        return f"RetrievalResult(id={self.doc_id}, score={self.score:.3f})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document": self.document,
            "metadata": self.metadata,
            "score": self.score,
            "doc_id": self.doc_id,
        }


class Retriever:
    """Retrieve relevant documents for queries."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
    ):
        """
        Initialize the retriever.

        Args:
            vector_store: Vector store instance (uses global if not provided)
            top_k: Number of documents to retrieve (defaults to settings value)
            min_score: Minimum similarity score (defaults to settings value)
        """
        settings = get_settings()
        self.vector_store = vector_store or get_vector_store()
        self.top_k = top_k if top_k is not None else settings.top_k_retrieval
        self.min_score = (
            min_score if min_score is not None else settings.min_similarity_score
        )

        logger.info(
            f"Retriever initialized with top_k={self.top_k}, "
            f"min_score={self.min_score}"
        )

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Query text
            top_k: Number of results to return (overrides instance default)
            min_score: Minimum similarity score (overrides instance default)
            metadata_filter: Optional metadata filters

        Returns:
            List[RetrievalResult]: Retrieved documents with scores

        Raises:
            ValueError: If query is invalid
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        k = top_k if top_k is not None else self.top_k
        min_s = min_score if min_score is not None else self.min_score

        logger.info(f"Retrieving documents for query: '{query[:100]}...'")

        try:
            # Query vector store
            results = self.vector_store.query(
                query_text=query, n_results=k, where=metadata_filter, min_score=min_s
            )

            # Convert to RetrievalResult objects
            retrieval_results = []

            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                document = results["documents"][0][i]
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]

                # Convert cosine distance to similarity score
                # Cosine distance ranges from 0 (identical) to 2 (opposite)
                # This maps [0, 2] -> [1, 0]
                score = 1 - (distance / 2)

                retrieval_results.append(
                    RetrievalResult(
                        document=document, metadata=metadata, score=score, doc_id=doc_id
                    )
                )

            logger.info(f"Retrieved {len(retrieval_results)} documents")

            # Sort by score (highest first)
            retrieval_results.sort(key=lambda x: x.score, reverse=True)

            return retrieval_results

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            raise RuntimeError(f"Retrieval failed: {e}")

    def retrieve_with_context(
        self, query: str, max_context_length: int = 4000, **kwargs
    ) -> Dict[str, Any]:
        """
        Retrieve documents and format as context string.

        Args:
            query: Query text
            max_context_length: Maximum character length for context
            **kwargs: Additional arguments passed to retrieve()

        Returns:
            Dict containing:
                - context: Formatted context string
                - sources: List of source documents
                - num_documents: Number of documents included
        """
        results = self.retrieve(query, **kwargs)

        if not results:
            return {
                "context": "No relevant information found.",
                "sources": [],
                "num_documents": 0,
            }

        # Build context string
        context_parts = []
        sources = []
        total_length = 0

        for i, result in enumerate(results, 1):
            # Format document with source
            source_info = result.metadata.get("source", "Unknown")
            doc_text = f"[Document {i}] (Source: {source_info})\n{result.document}\n"

            # Check if adding this would exceed max length
            if total_length + len(doc_text) > max_context_length:
                if not context_parts:
                    # If first document is too long, truncate it
                    doc_text = doc_text[:max_context_length] + "...\n"
                    context_parts.append(doc_text)
                    sources.append(result.to_dict())
                break

            context_parts.append(doc_text)
            sources.append(result.to_dict())
            total_length += len(doc_text)

        context = "\n".join(context_parts)

        return {"context": context, "sources": sources, "num_documents": len(sources)}

    def get_similar_documents(
        self, document_id: str, top_k: Optional[int] = None
    ) -> List[RetrievalResult]:
        """
        Find documents similar to a given document.

        Args:
            document_id: ID of the reference document
            top_k: Number of similar documents to return

        Returns:
            List[RetrievalResult]: Similar documents
        """
        # Get the reference document
        doc = self.vector_store.get_document(document_id)

        if not doc:
            raise ValueError(f"Document not found: {document_id}")

        # Use the document text as query
        results = self.retrieve(
            query=doc["document"],
            top_k=(top_k or self.top_k) + 1,  # +1 to account for self-match
        )

        # Filter out the reference document itself
        filtered_results = [r for r in results if r.doc_id != document_id]

        return filtered_results[: top_k or self.top_k]


# Global instance
_retriever: Optional[Retriever] = None


def get_retriever() -> Retriever:
    """
    Get or create a global retriever instance.

    Returns:
        Retriever: The retriever instance
    """
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever
