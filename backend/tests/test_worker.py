import pytest

from app import worker
from app.cache import MEETINGS_GENERATION_KEY
from app.models import Meeting, MeetingStatus
from app.redis_client import TaskQueue


@pytest.fixture
def task_queue(fake_redis, monkeypatch):
    queue = TaskQueue(fake_redis)
    monkeypatch.setattr(worker, "_task_queue", queue)
    return queue


@pytest.fixture
def queued_job(task_queue, db_session, tmp_path):
    audio = tmp_path / "meeting.wav"
    audio.write_bytes(b"fake audio")
    meeting = Meeting(filename="meeting.wav", status=MeetingStatus.QUEUED,
                      file_path=str(audio))
    db_session.add(meeting)
    db_session.commit()
    task_queue.enqueue_meeting_job(meeting.id, str(audio), "meeting.wav")
    return task_queue.get_next_job()


def test_process_job_stores_results(queued_job, fake_transcribe, db_session,
                                    fake_redis):
    result = worker.process_meeting_job(queued_job)

    assert result["language"] == "en"
    meeting = db_session.get(Meeting, queued_job["meeting_id"])
    assert meeting.status == MeetingStatus.COMPLETED
    assert meeting.duration_seconds == 42.5
    assert "budget" in meeting.keywords.split(",")
    assert meeting.summary
    # Caches were invalidated when processing started and finished.
    assert fake_redis.get(MEETINGS_GENERATION_KEY) == "2"


def test_job_for_deleted_meeting_is_skipped(queued_job, fake_transcribe,
                                            db_session):
    db_session.delete(db_session.get(Meeting, queued_job["meeting_id"]))
    db_session.commit()

    assert worker.process_meeting_job(queued_job) == {
        "skipped": "meeting deleted"}
    assert fake_transcribe == []


def test_failed_job_is_retried_then_marked_failed(queued_job, task_queue,
                                                  db_session, monkeypatch):
    def broken(file_path):
        raise RuntimeError("corrupt audio")

    monkeypatch.setattr(worker.processing, "transcribe", broken)
    meeting_id = queued_job["meeting_id"]

    job = queued_job
    for attempt in range(1, job["max_attempts"] + 1):
        with pytest.raises(RuntimeError):
            worker.process_meeting_job(job)
        worker.handle_job_failure(job, RuntimeError("corrupt audio"))

        db_session.expire_all()
        meeting = db_session.get(Meeting, meeting_id)
        assert meeting.error_message == "corrupt audio"
        if attempt < job["max_attempts"]:
            assert meeting.status == MeetingStatus.QUEUED
            job = task_queue.get_next_job()
        else:
            assert meeting.status == MeetingStatus.FAILED
            assert task_queue.get_queue_length() == 0
