-- Track processing status, failure reason and the stored upload path.

-- Rows created before status tracking existed are treated as completed;
-- new rows start out queued.
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'completed';
ALTER TABLE meetings ALTER COLUMN status SET DEFAULT 'queued';

ALTER TABLE meetings ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS file_path TEXT;

CREATE INDEX IF NOT EXISTS idx_meetings_status ON meetings(status);
