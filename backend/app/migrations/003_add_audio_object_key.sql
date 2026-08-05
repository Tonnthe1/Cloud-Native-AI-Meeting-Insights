ALTER TABLE meetings
ADD COLUMN IF NOT EXISTS audio_object_key VARCHAR(512);

CREATE INDEX IF NOT EXISTS ix_meetings_audio_object_key
ON meetings (audio_object_key);
