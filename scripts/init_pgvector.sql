-- Initialize PostgreSQL with pgvector extension for RapidAssist
-- This script runs automatically when the container first starts

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the documents table with vector column
-- The embedding dimension is 1536 (for text-embedding-3-small)
-- This can be adjusted based on the embedding model used
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for cosine similarity search (IVFFlat)
-- This provides approximate nearest neighbor search for better performance
-- The 'lists' parameter should be approximately sqrt(n) where n is the number of rows
-- 100 is a good starting point for up to 10,000 documents
CREATE INDEX IF NOT EXISTS documents_embedding_idx
ON documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create index for metadata searches
CREATE INDEX IF NOT EXISTS documents_metadata_idx
ON documents
USING gin (metadata);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (adjust as needed for your setup)
-- These are not needed for the default setup but included for reference
-- GRANT ALL PRIVILEGES ON TABLE documents TO rapidassist;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO rapidassist;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'pgvector initialization complete. Table "documents" is ready.';
END $$;
