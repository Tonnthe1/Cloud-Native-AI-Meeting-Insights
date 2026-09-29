import os
import tempfile

# Configure the app before it's imported: a throwaway SQLite database and no
# API key or OpenAI key, regardless of the developer's .env.
_tmp_dir = tempfile.mkdtemp(prefix="meeting-insights-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_dir}/test.db"
os.environ["API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""

import fakeredis  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import main, processing  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402

SAMPLE_TRANSCRIPT = (
    "Welcome to the quarterly budget review. "
    "The marketing budget increased by ten percent this quarter. "
    "Sarah will prepare the budget report for the board by Friday. "
    "We decided to postpone the office move until next year. "
    "Finally, the hiring plan for engineering was approved."
)


@pytest.fixture(autouse=True)
def fresh_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def fake_redis():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    path = tmp_path / "uploads"
    monkeypatch.setattr(main, "UPLOAD_DIR", path)
    return path


@pytest.fixture
def fake_transcribe(monkeypatch):
    """Replace faster-whisper with a canned transcription."""
    calls = []

    def transcribe(file_path):
        calls.append(file_path)
        return processing.Transcription(
            text=SAMPLE_TRANSCRIPT, language="en", duration_seconds=42.5)

    monkeypatch.setattr(processing, "transcribe", transcribe)
    return calls


@pytest.fixture
def make_client(monkeypatch, upload_dir, fake_redis):
    """Build a TestClient whose app uses the given Redis client."""
    clients = []

    def _make(redis_client=fake_redis):
        monkeypatch.setattr(main, "get_redis_client",
                            lambda **kwargs: redis_client)
        client = TestClient(main.app)
        client.__enter__()  # run the lifespan
        clients.append(client)
        return client

    yield _make
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(make_client):
    return make_client()


def upload(client, name="standup.wav", content=b"RIFF fake audio",
           content_type="audio/wav"):
    return client.post("/analyze-meeting",
                       files={"file": (name, content, content_type)})
