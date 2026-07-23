from io import BytesIO
from pathlib import Path

import pytest

from app.storage import LocalObjectStore, S3ObjectStore, build_object_key


class FakeS3Client:
    def __init__(self):
        self.objects = {}
        self.extra_args = None

    def head_bucket(self, Bucket):
        assert Bucket == "meetings"

    def upload_fileobj(self, fileobj, bucket, key, **kwargs):
        assert bucket == "meetings"
        self.objects[key] = fileobj.read()
        self.extra_args = kwargs.get("ExtraArgs")

    def download_file(self, bucket, key, destination):
        assert bucket == "meetings"
        Path(destination).write_bytes(self.objects[key])

    def delete_object(self, Bucket, Key):
        assert Bucket == "meetings"
        self.objects.pop(Key, None)


def test_local_object_store_round_trip(tmp_path):
    store = LocalObjectStore(tmp_path / "objects")
    key = "meetings/example.wav"

    store.put_fileobj(BytesIO(b"audio-bytes"), key, "audio/wav")
    with store.materialize(key) as materialized:
        assert materialized.suffix == ".wav"
        assert materialized.read_bytes() == b"audio-bytes"

    store.delete(key)
    with pytest.raises(FileNotFoundError):
        store.download(key, tmp_path / "missing.wav")


def test_local_object_store_rejects_path_traversal(tmp_path):
    store = LocalObjectStore(tmp_path / "objects")

    with pytest.raises(ValueError):
        store.put_fileobj(BytesIO(b"bad"), "../outside.wav")


def test_s3_object_store_round_trip(tmp_path):
    client = FakeS3Client()
    store = S3ObjectStore(bucket="meetings", client=client)
    key = "meetings/example.mp3"

    store.put_fileobj(BytesIO(b"remote-audio"), key, "audio/mpeg")
    destination = tmp_path / "download.mp3"
    store.download(key, destination)

    assert destination.read_bytes() == b"remote-audio"
    assert client.extra_args == {"ContentType": "audio/mpeg"}

    store.delete(key)
    assert key not in client.objects


def test_object_keys_are_randomized_and_preserve_safe_suffixes():
    first = build_object_key("customer interview.MP3")
    second = build_object_key("customer interview.MP3")

    assert first.startswith("meetings/")
    assert first.endswith(".mp3")
    assert first != second
    assert build_object_key("unsafe.../../secret").startswith("meetings/")
