"""Object storage abstraction shared by API and worker processes."""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator, Optional

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError


class ObjectStore:
    """Minimal interface required by the meeting processing pipeline."""

    def put_fileobj(
        self,
        fileobj: BinaryIO,
        object_key: str,
        content_type: Optional[str] = None,
    ) -> None:
        raise NotImplementedError

    def download(self, object_key: str, destination: Path) -> None:
        raise NotImplementedError

    def delete(self, object_key: str) -> None:
        raise NotImplementedError

    @contextmanager
    def materialize(self, object_key: str) -> Iterator[Path]:
        suffix = Path(object_key).suffix
        with tempfile.TemporaryDirectory(prefix="meeting-insights-") as temp_dir:
            destination = Path(temp_dir) / f"source{suffix}"
            self.download(object_key, destination)
            yield destination


class LocalObjectStore(ObjectStore):
    """Filesystem implementation for development and single-host deployments."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, object_key: str) -> Path:
        candidate = (self.root / object_key).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise ValueError("Invalid object key")
        return candidate

    def put_fileobj(
        self,
        fileobj: BinaryIO,
        object_key: str,
        content_type: Optional[str] = None,
    ) -> None:
        del content_type
        destination = self._path(object_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as output:
            shutil.copyfileobj(fileobj, output)

    def download(self, object_key: str, destination: Path) -> None:
        source = self._path(object_key)
        if not source.exists():
            raise FileNotFoundError(f"Stored object not found: {object_key}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    def delete(self, object_key: str) -> None:
        self._path(object_key).unlink(missing_ok=True)


class S3ObjectStore(ObjectStore):
    """S3-compatible implementation supporting AWS S3 and MinIO."""

    def __init__(self, bucket: str, client: BaseClient):
        self.bucket = bucket
        self.client = client
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return
        except ClientError as exc:
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            error_code = exc.response.get("Error", {}).get("Code")
            if status_code not in {403, 404} and error_code not in {
                "404",
                "NoSuchBucket",
                "NotFound",
            }:
                raise

        region = os.getenv("AWS_REGION", "us-east-1")
        kwargs = {"Bucket": self.bucket}
        if region != "us-east-1" and not os.getenv("S3_ENDPOINT_URL"):
            kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
        self.client.create_bucket(**kwargs)

    def put_fileobj(
        self,
        fileobj: BinaryIO,
        object_key: str,
        content_type: Optional[str] = None,
    ) -> None:
        extra_args = {"ContentType": content_type} if content_type else None
        self.client.upload_fileobj(
            fileobj,
            self.bucket,
            object_key,
            ExtraArgs=extra_args,
        )

    def download(self, object_key: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, object_key, str(destination))

    def delete(self, object_key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=object_key)


def build_object_key(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if len(suffix) > 12 or any(character not in ".abcdefghijklmnopqrstuvwxyz0123456789" for character in suffix):
        suffix = ""
    return f"meetings/{uuid.uuid4().hex}{suffix}"


def get_object_store() -> ObjectStore:
    backend = os.getenv("STORAGE_BACKEND", "local").strip().lower()
    if backend == "local":
        root = Path(os.getenv("STORAGE_LOCAL_DIR", os.getenv("UPLOAD_DIR", "/app/uploads")))
        return LocalObjectStore(root)
    if backend != "s3":
        raise ValueError(f"Unsupported STORAGE_BACKEND: {backend}")

    bucket = os.getenv("S3_BUCKET", "meeting-insights")
    client = boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL") or None,
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID") or None,
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY") or None,
    )
    return S3ObjectStore(bucket=bucket, client=client)
