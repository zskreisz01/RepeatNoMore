"""Vector store management using PostgreSQL with pgvector."""

import json
from typing import List, Dict, Any, Optional
import logging

import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from pgvector.psycopg2 import register_vector

from app.config import get_settings
from app.rag.embeddings import get_embedding_generator

logger = logging.getLogger(__name__)


class VectorStore:
    """Manage document storage and retrieval using PostgreSQL with pgvector."""

    def __init__(self, table_name: Optional[str] = None, reset: bool = False):
        """
        Initialize the vector store.

        Args:
            table_name: Name of the table to use
            reset: Whether to reset the table on initialization
        """
        settings = get_settings()
        self.table_name = table_name or settings.postgres_vector_table
        self.embedding_generator = get_embedding_generator()
        self.embedding_dim = settings.embedding_dimension

        # Connection parameters
        self.conn_params = {
            "host": settings.postgres_host,
            "port": settings.postgres_port,
            "dbname": settings.postgres_db,
            "user": settings.postgres_user,
            "password": settings.postgres_password,
        }

        logger.info(
            f"Connecting to PostgreSQL at {settings.postgres_host}:{settings.postgres_port}"
        )

        # Initialize connection and setup
        self._setup_database(reset)
        logger.info(f"Vector store initialized with table: {self.table_name}")

    def _get_connection(self):
        """Get a database connection with pgvector registered."""
        conn = psycopg2.connect(**self.conn_params)
        register_vector(conn)
        return conn

    def _setup_database(self, reset: bool = False):
        """Set up the database schema."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Enable pgvector extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

                if reset:
                    logger.warning(f"Resetting table: {self.table_name}")
                    cur.execute(f"DROP TABLE IF EXISTS {self.table_name}")

                # Create table with vector column
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        metadata JSONB DEFAULT '{{}}',
                        embedding vector({self.embedding_dim})
                    )
                """)

                # Create index for cosine similarity search
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx
                    ON {self.table_name}
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """)

            conn.commit()

    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Add documents to the vector store.

        Args:
            texts: List of document texts
            metadatas: Optional list of metadata dictionaries
            ids: Optional list of document IDs (auto-generated if not provided)

        Returns:
            List[str]: List of document IDs

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If adding documents fails
        """
        if not texts:
            raise ValueError("Cannot add empty document list")

        # Generate IDs if not provided
        if ids is None:
            existing_count = self.count()
            ids = [f"doc_{existing_count + i}" for i in range(len(texts))]

        # Ensure metadatas list exists
        if metadatas is None:
            metadatas = [{} for _ in texts]
        else:
            metadatas = [meta if meta else {} for meta in metadatas]

        if len(texts) != len(metadatas) or len(texts) != len(ids):
            raise ValueError("texts, metadatas, and ids must have the same length")

        try:
            logger.info(f"Adding {len(texts)} documents to vector store")

            # Generate embeddings
            embeddings = self.embedding_generator.embed_batch(texts)

            # Prepare data for insertion
            data = [
                (doc_id, text, json.dumps(meta), embedding)
                for doc_id, text, meta, embedding in zip(
                    ids, texts, metadatas, embeddings
                )
            ]

            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Use upsert to handle duplicate IDs
                    execute_values(
                        cur,
                        f"""
                        INSERT INTO {self.table_name} (id, content, metadata, embedding)
                        VALUES %s
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            metadata = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding
                        """,
                        data,
                        template="(%s, %s, %s, %s::vector)",
                    )
                conn.commit()

            logger.info(f"Successfully added {len(texts)} documents")
            return ids

        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise RuntimeError(f"Failed to add documents: {e}")

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        min_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Query the vector store for similar documents.

        Args:
            query_text: Query text
            n_results: Number of results to return
            where: Optional metadata filters (supports simple equality)
            min_score: Minimum similarity score (0-1)

        Returns:
            Dict containing:
                - ids: List of document IDs (nested for legacy compatibility)
                - documents: List of document texts (nested)
                - metadatas: List of metadata dictionaries (nested)
                - distances: List of distance scores (nested)

        Raises:
            ValueError: If query is invalid
            RuntimeError: If query fails
        """
        if not query_text or not query_text.strip():
            raise ValueError("Query text cannot be empty")

        try:
            logger.info(f"Querying vector store: '{query_text[:50]}...'")

            # Generate query embedding
            query_embedding = self.embedding_generator.embed_text(query_text)

            # Build the query
            query_sql = f"""
                SELECT
                    id,
                    content,
                    metadata,
                    embedding <=> %s::vector AS distance
                FROM {self.table_name}
            """

            params = [query_embedding]

            # Add metadata filter if provided
            if where:
                # Simple equality filter for metadata
                conditions = []
                for key, value in where.items():
                    conditions.append(f"metadata->>'{key}' = %s")
                    params.append(str(value))
                query_sql += " WHERE " + " AND ".join(conditions)

            # Add distance filter if min_score is specified
            # Cosine distance: 0 = identical, 2 = opposite
            # Score = 1 - (distance / 2), so distance = 2 * (1 - score)
            if min_score is not None:
                max_distance = 2 * (1 - min_score)
                if where:
                    query_sql += f" AND embedding <=> %s::vector <= {max_distance}"
                else:
                    query_sql += f" WHERE embedding <=> %s::vector <= {max_distance}"
                params.append(query_embedding)

            query_sql += f" ORDER BY distance LIMIT {n_results}"

            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query_sql, params)
                    rows = cur.fetchall()

            # Format results for legacy compatibility (nested lists)
            results = {
                "ids": [[row["id"] for row in rows]],
                "documents": [[row["content"] for row in rows]],
                "metadatas": [[row["metadata"] for row in rows]],
                "distances": [[row["distance"] for row in rows]],
            }

            logger.info(f"Found {len(results['ids'][0])} matching documents")
            return results

        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise RuntimeError(f"Query failed: {e}")

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific document by ID.

        Args:
            doc_id: Document ID

        Returns:
            Dict with document data or None if not found
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        f"SELECT id, content, metadata FROM {self.table_name} WHERE id = %s",
                        (doc_id,),
                    )
                    row = cur.fetchone()

            if row:
                return {
                    "id": row["id"],
                    "document": row["content"],
                    "metadata": row["metadata"],
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None

    def get_ids_by_metadata(self, filters: Dict[str, Any]) -> List[str]:
        """
        Get document IDs matching metadata filters.

        Args:
            filters: Dictionary of metadata key-value pairs to match

        Returns:
            List of document IDs matching the filters
        """
        try:
            if not filters:
                return []

            conditions = []
            params = []
            for key, value in filters.items():
                conditions.append(f"metadata->>'{key}' = %s")
                params.append(str(value))

            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT id FROM {self.table_name} WHERE " + " AND ".join(conditions),
                        params,
                    )
                    rows = cur.fetchall()

            return [row[0] for row in rows]

        except Exception as e:
            logger.error(f"Failed to get IDs by metadata: {e}")
            return []

    def delete_documents(self, ids: List[str]) -> bool:
        """
        Delete documents from the vector store.

        Args:
            ids: List of document IDs to delete

        Returns:
            bool: True if successful
        """
        try:
            logger.info(f"Deleting {len(ids)} documents")

            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"DELETE FROM {self.table_name} WHERE id = ANY(%s)", (ids,)
                    )
                conn.commit()

            logger.info("Documents deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return False

    def update_document(
        self,
        doc_id: str,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update a document in the vector store.

        Args:
            doc_id: Document ID
            text: New document text (optional)
            metadata: New metadata (optional)

        Returns:
            bool: True if successful
        """
        try:
            updates = []
            params = []

            if text is not None:
                embedding = self.embedding_generator.embed_text(text)
                updates.append("content = %s")
                params.append(text)
                updates.append("embedding = %s::vector")
                params.append(embedding)

            if metadata is not None:
                updates.append("metadata = %s")
                params.append(json.dumps(metadata))

            if not updates:
                return True  # Nothing to update

            params.append(doc_id)

            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"UPDATE {self.table_name} SET {', '.join(updates)} WHERE id = %s",
                        params,
                    )
                conn.commit()

            logger.info(f"Updated document {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return False

    def count(self) -> int:
        """
        Get the number of documents in the table.

        Returns:
            int: Document count
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                    result = cur.fetchone()
                    return result[0] if result else 0
        except Exception:
            # Table might not exist yet
            return 0

    def clear(self) -> bool:
        """
        Clear all documents from the table.

        Returns:
            bool: True if successful
        """
        try:
            logger.warning(f"Clearing all documents from {self.table_name}")

            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"TRUNCATE TABLE {self.table_name}")
                conn.commit()

            logger.info("Table cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to clear table: {e}")
            return False


# Global instance
_vector_store: Optional[VectorStore] = None


def get_vector_store(reset: bool = False) -> VectorStore:
    """
    Get or create a global vector store instance.

    Args:
        reset: Whether to reset the table

    Returns:
        VectorStore: The vector store instance
    """
    global _vector_store
    if _vector_store is None or reset:
        _vector_store = VectorStore(reset=reset)
    return _vector_store
