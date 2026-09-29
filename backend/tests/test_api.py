import json

import redis

from app import main
from app.models import Meeting, MeetingStatus
from conftest import upload


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_meeting_queues_job(client, fake_redis, upload_dir,
                                    db_session):
    response = upload(client)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"

    meeting = db_session.get(Meeting, body["meeting_id"])
    assert meeting.status == MeetingStatus.QUEUED
    assert meeting.filename == "standup.wav"

    job = json.loads(fake_redis.lindex("meeting_processing_queue", 0))
    assert job["id"] == body["job_id"]
    assert job["meeting_id"] == meeting.id
    assert job["file_path"] == meeting.file_path
    stored = upload_dir / job["file_path"].rsplit("/", 1)[-1]
    assert stored.read_bytes() == b"RIFF fake audio"


def test_uploads_with_same_name_are_stored_separately(client, upload_dir):
    upload(client, content=b"first")
    upload(client, content=b"second")

    contents = sorted(p.read_bytes() for p in upload_dir.iterdir())
    assert contents == [b"first", b"second"]


def test_rejects_non_audio_upload(client, upload_dir, db_session):
    response = upload(client, name="notes.txt", content=b"hello",
                      content_type="text/plain")

    assert response.status_code == 415
    assert db_session.query(Meeting).count() == 0
    assert not upload_dir.exists() or not any(upload_dir.iterdir())


def test_rejects_oversized_upload(client, upload_dir, monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD_MB", 0)

    response = upload(client)

    assert response.status_code == 413
    assert not any(upload_dir.iterdir())


def test_rejects_empty_upload(client):
    assert upload(client, content=b"").status_code == 400


def test_processes_synchronously_when_worker_disabled(
        client, fake_transcribe, monkeypatch, db_session):
    monkeypatch.setattr(main, "USE_WORKER_SERVICE", False)

    response = upload(client)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["language"] == "en"
    assert body["duration_seconds"] == 42.5
    assert "budget" in body["keywords"]
    # No OpenAI key in tests, so the summary is extractive.
    assert body["summary"].startswith("• ")

    meeting = db_session.get(Meeting, body["meeting_id"])
    assert meeting.status == MeetingStatus.COMPLETED
    assert fake_transcribe == [meeting.file_path]


def test_falls_back_to_sync_processing_when_redis_is_down(
        make_client, fake_transcribe):
    unreachable = redis.Redis(host="127.0.0.1", port=1,
                              socket_connect_timeout=0.2,
                              decode_responses=True)
    client = make_client(unreachable)

    response = upload(client)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    # Listing still works without the cache.
    meetings = client.get("/meetings")
    assert meetings.status_code == 200
    assert len(meetings.json()) == 1


def test_sync_processing_failure_marks_meeting_failed(
        client, monkeypatch, db_session):
    monkeypatch.setattr(main, "USE_WORKER_SERVICE", False)

    def broken_transcribe(file_path):
        raise RuntimeError("decoder exploded")

    monkeypatch.setattr(main.processing, "transcribe", broken_transcribe)

    response = upload(client)

    assert response.status_code == 500
    meeting = db_session.query(Meeting).one()
    assert meeting.status == MeetingStatus.FAILED
    assert meeting.error_message == "decoder exploded"


def test_meeting_detail_and_list(client, db_session):
    meeting_id = upload(client).json()["meeting_id"]
    meeting = db_session.get(Meeting, meeting_id)
    meeting.keywords = "budget,hiring"
    db_session.commit()

    detail = client.get(f"/meetings/{meeting_id}").json()
    assert detail["status"] == "queued"
    assert detail["keywords"] == ["budget", "hiring"]
    # Timestamps are UTC and say so.
    assert detail["created_at"].endswith(("Z", "+00:00"))

    listed = client.get("/meetings").json()
    assert [m["id"] for m in listed] == [meeting_id]


def test_meeting_not_found(client):
    assert client.get("/meetings/999").status_code == 404
    assert client.delete("/meetings/999").status_code == 404


def test_list_is_cached_and_invalidated(client, db_session):
    assert client.get("/meetings").json() == []

    # Written directly to the DB, so nothing invalidates the cache.
    db_session.add(Meeting(filename="direct.wav", status="completed"))
    db_session.commit()
    assert client.get("/meetings").json() == []

    # An upload invalidates the cache; both meetings are now listed, and
    # the response served from the cache has the same shape.
    upload(client)
    first = client.get("/meetings").json()
    second = client.get("/meetings").json()
    assert len(first) == 2
    assert first == second


def test_list_pagination(client):
    ids = [upload(client).json()["meeting_id"] for _ in range(3)]

    page = client.get("/meetings", params={"limit": 2, "offset": 1}).json()

    assert [m["id"] for m in page] == [ids[1], ids[0]]


def test_delete_removes_meeting_and_file(client, upload_dir):
    meeting_id = upload(client).json()["meeting_id"]
    assert len(list(upload_dir.iterdir())) == 1

    assert client.delete(f"/meetings/{meeting_id}").json() == {"ok": True}

    assert client.get(f"/meetings/{meeting_id}").status_code == 404
    assert client.get("/meetings").json() == []
    assert not any(upload_dir.iterdir())


def test_search(client, db_session):
    db_session.add_all([
        Meeting(filename="a.wav", transcript="Discussed the budget",
                status="completed"),
        Meeting(filename="b.wav", transcript="Hiring at 100% capacity",
                status="completed"),
    ])
    db_session.commit()

    budget = client.get("/search", params={"q": "BUDGET"}).json()
    assert [m["filename"] for m in budget] == ["a.wav"]

    # LIKE wildcards are matched literally.
    percent = client.get("/search", params={"q": "%"}).json()
    assert [m["filename"] for m in percent] == ["b.wav"]


def test_api_key_is_enforced_when_configured(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "s3cret")

    assert client.get("/meetings").status_code == 401
    wrong = client.get("/meetings", headers={"X-API-Key": "nope"})
    assert wrong.status_code == 401
    ok = client.get("/meetings", headers={"X-API-Key": "s3cret"})
    assert ok.status_code == 200
    # Health checks stay open for load balancers and probes.
    assert client.get("/health").status_code == 200


def test_job_status(client):
    job_id = upload(client).json()["job_id"]

    job = client.get(f"/job-status/{job_id}").json()
    assert job["status"] == "queued"
    assert client.get("/job-status/unknown").status_code == 404


def test_summarize_without_openai_key(client):
    response = client.post("/summarize", params={
        "transcript": "We agreed to ship the release on Monday morning."})

    assert response.json()["summary"] == (
        "• We agreed to ship the release on Monday morning.")
