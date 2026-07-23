import os
from io import BytesIO

import pytest

from app.storage import build_object_key, get_object_store


@pytest.mark.skipif(
    os.getenv("RUN_STORAGE_INTEGRATION") != "1",
    reason="Set RUN_STORAGE_INTEGRATION=1 with an S3-compatible service",
)
def test_s3_compatible_storage_round_trip():
    store = get_object_store()
    object_key = build_object_key("integration.wav")

    try:
        store.put_fileobj(BytesIO(b"integration-audio"), object_key, "audio/wav")
        with store.materialize(object_key) as downloaded:
            assert downloaded.read_bytes() == b"integration-audio"
    finally:
        store.delete(object_key)
