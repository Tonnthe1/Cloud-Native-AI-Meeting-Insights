-- Performance optimization indexes for meeting insights
-- Run this migration to improve query performance

-- Index on created_at for chronological queries (most common access pattern)
CREATE INDEX IF NOT EXISTS idx_meetings_created_at ON meetings(created_at DESC);

-- Composite index on filename and language for filtered searches
CREATE INDEX IF NOT EXISTS idx_meetings_filename_language ON meetings(filename, language);

-- Index on language for language-specific queries
CREATE INDEX IF NOT EXISTS idx_meetings_language ON meetings(language);

-- Add trigram extension for full-text search if not exists
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- GIN index on transcript for fast trigram search
CREATE INDEX IF NOT EXISTS idx_meetings_transcript_gin ON meetings USING gin(transcript gin_trgm_ops);

-- GIN index on summary for search
CREATE INDEX IF NOT EXISTS idx_meetings_summary_gin ON meetings USING gin(summary gin_trgm_ops);

-- Index on keywords for keyword-based searches
CREATE INDEX IF NOT EXISTS idx_meetings_keywords ON meetings(keywords);

-- Analyze tables to update statistics
ANALYZE meetings;