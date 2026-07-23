ALTER TABLE meetings
    ADD COLUMN IF NOT EXISTS insights_json TEXT,
    ADD COLUMN IF NOT EXISTS insight_provider VARCHAR(64),
    ADD COLUMN IF NOT EXISTS processing_status VARCHAR(32) NOT NULL DEFAULT 'queued';

CREATE INDEX IF NOT EXISTS idx_meetings_processing_status
    ON meetings(processing_status);
