import os

import pytest


@pytest.mark.skipif(
    os.getenv("RUN_PIPELINE_INTEGRATION") != "1",
    reason="Requires PostgreSQL, Redis, and S3-compatible storage",
)
def test_upload_queue_worker_database_pipeline(monkeypatch):
    from fastapi.testclient import TestClient

    import app.worker as worker
    from app.db import Base, SessionLocal, engine
    from app.main import app
    from app.models import Meeting
    from app.redis_client import TaskQueue, get_redis_client

    redis_client = get_redis_client()
    redis_client.flushdb()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    worker.initialize_services()

    transcript = (
        "We agreed to ship the private beta on Friday. "
        "Alex will prepare the launch checklist. "
        "The security review remains a risk."
    )
    monkeypatch.setattr(
        worker,
        "transcribe_audio",
        lambda _path: (transcript, "en"),
    )
    monkeypatch.setattr(
        worker,
        "get_audio_duration_seconds",
        lambda _path: 42.5,
    )

    object_key = None
    with TestClient(app) as client:
        upload = client.post(
            "/analyze-meeting",
            files={"file": ("planning.wav", b"fake-audio", "audio/wav")},
        )
        assert upload.status_code == 200, upload.text
        queued = upload.json()
        assert queued["status"] == "queued"

        queue = TaskQueue(redis_client)
        job = queue.get_next_job()
        assert job is not None
        assert job["id"] == queued["job_id"]
        object_key = job["object_key"]
        assert object_key.startswith("meetings/")

        result = worker.process_meeting_job(job)
        queue.complete_job(job["id"], result)

        status = client.get(f"/job-status/{job['id']}")
        assert status.status_code == 200
        assert status.json()["status"] == "completed"

        meeting_response = client.get(f"/meetings/{queued['meeting_id']}")
        assert meeting_response.status_code == 200
        payload = meeting_response.json()
        assert payload["transcript"] == transcript
        assert payload["status"] == "completed"
        assert payload["insights"]["decisions"]
        assert payload["insights"]["action_items"]
        assert payload["insights"]["risks"]

    db = SessionLocal()
    try:
        meeting = db.get(Meeting, queued["meeting_id"])
        assert meeting is not None
        assert meeting.language == "en"
        assert meeting.duration_seconds == 42.5
        assert meeting.insight_provider == "local-heuristic"
    finally:
        db.close()

    if object_key and worker._object_store is not None:
        worker._object_store.delete(object_key)
