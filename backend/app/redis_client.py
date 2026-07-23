import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis
import redis.asyncio as async_redis


class QueueFullError(RuntimeError):
    pass


def _connection_kwargs() -> Dict[str, Any]:
    return {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", "6379")),
        "db": int(os.getenv("REDIS_DB", "0")),
        "password": os.getenv("REDIS_PASSWORD") or None,
        "decode_responses": True,
        "socket_connect_timeout": 5,
        "health_check_interval": 30,
    }


def get_redis_client() -> redis.Redis:
    return redis.Redis(**_connection_kwargs())


def get_async_redis_client() -> async_redis.Redis:
    return async_redis.Redis(**_connection_kwargs())


class TaskQueue:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.queue_name = "meeting_processing_queue"
        self.processing_set = "processing_meetings"
        self.max_queue_size = int(os.getenv("MAX_QUEUE_SIZE", "100"))
        self.job_ttl_seconds = int(os.getenv("JOB_TTL_SECONDS", "86400"))

    def enqueue_meeting_job(
        self,
        meeting_id: int,
        object_key: str,
        filename: str,
    ) -> str:
        if self.get_queue_length() >= self.max_queue_size:
            raise QueueFullError(
                f"Processing queue is full ({self.max_queue_size} jobs)"
            )

        timestamp = int(datetime.now(timezone.utc).timestamp())
        job_data = {
            "id": f"meeting_{meeting_id}_{timestamp}",
            "meeting_id": meeting_id,
            "object_key": object_key,
            "filename": filename,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "attempts": 0,
            "max_attempts": int(os.getenv("MAX_JOB_ATTEMPTS", "3")),
        }
        encoded = json.dumps(job_data)
        with self.redis.pipeline(transaction=True) as pipe:
            pipe.lpush(self.queue_name, encoded)
            pipe.setex(f"job:{job_data['id']}", self.job_ttl_seconds, encoded)
            pipe.execute()
        return job_data["id"]

    def get_next_job(self) -> Optional[Dict[str, Any]]:
        result = self.redis.brpop(self.queue_name, timeout=30)
        if not result:
            return None

        _, job_json = result
        job_data = json.loads(job_json)
        job_data["status"] = "processing"
        job_data["started_at"] = datetime.now(timezone.utc).isoformat()
        encoded = json.dumps(job_data)
        with self.redis.pipeline(transaction=True) as pipe:
            pipe.sadd(self.processing_set, job_data["id"])
            pipe.setex(f"job:{job_data['id']}", self.job_ttl_seconds, encoded)
            pipe.execute()
        return job_data

    def complete_job(
        self,
        job_id: str,
        result_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        job_data = self.get_job_status(job_id)
        if not job_data:
            return
        job_data.update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "result": result_data or {},
        })
        with self.redis.pipeline(transaction=True) as pipe:
            pipe.srem(self.processing_set, job_id)
            pipe.setex(f"job:{job_id}", 3600, json.dumps(job_data))
            pipe.execute()

    def fail_job(
        self,
        job_id: str,
        error_message: str,
        retry: bool = True,
    ) -> None:
        job_data = self.get_job_status(job_id)
        if not job_data:
            return
        job_data["attempts"] = int(job_data.get("attempts", 0)) + 1
        job_data["last_error"] = error_message
        job_data["failed_at"] = datetime.now(timezone.utc).isoformat()

        should_retry = (
            retry and job_data["attempts"] < job_data["max_attempts"]
        )
        job_data["status"] = "queued" if should_retry else "failed"
        encoded = json.dumps(job_data)
        with self.redis.pipeline(transaction=True) as pipe:
            pipe.srem(self.processing_set, job_id)
            if should_retry:
                pipe.lpush(self.queue_name, encoded)
            pipe.setex(f"job:{job_id}", 3600, encoded)
            pipe.execute()

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        job_json = self.redis.get(f"job:{job_id}")
        return json.loads(job_json) if job_json else None

    def get_queue_length(self) -> int:
        return self.redis.llen(self.queue_name)

    def get_processing_count(self) -> int:
        return self.redis.scard(self.processing_set)
