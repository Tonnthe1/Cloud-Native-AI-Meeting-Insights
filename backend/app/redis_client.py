import os
import redis
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone


def get_redis_client():
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))
    redis_password = os.getenv("REDIS_PASSWORD", None)

    return redis.Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password,
        decode_responses=True
    )


class TaskQueue:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.queue_name = "meeting_processing_queue"
        self.processing_set = "processing_meetings"

    def enqueue_meeting_job(self, meeting_id: int, file_path: str,
                            filename: str) -> str:
        """Enqueue a new meeting processing job."""
        timestamp = int(datetime.now(timezone.utc).timestamp())
        job_data = {
            "id": f"meeting_{meeting_id}_{timestamp}",
            "meeting_id": meeting_id,
            "file_path": file_path,
            "filename": filename,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "attempts": 0,
            "max_attempts": 3
        }

        # Add to queue
        self.redis.lpush(self.queue_name, json.dumps(job_data))

        # Store job details with expiration (24 hours)
        self.redis.setex(
            f"job:{job_data['id']}",
            86400,
            json.dumps(job_data)
        )

        return job_data["id"]

    def get_next_job(self) -> Optional[Dict[str, Any]]:
        """Get the next job from the queue (blocking operation)."""
        result = self.redis.brpop(self.queue_name, timeout=30)
        if result:
            _, job_json = result
            job_data = json.loads(job_json)

            # Mark as processing
            self.redis.sadd(self.processing_set, job_data["id"])
            job_data["status"] = "processing"
            job_data["started_at"] = datetime.now(timezone.utc).isoformat()

            # Update job details
            self.redis.setex(
                f"job:{job_data['id']}",
                86400,
                json.dumps(job_data)
            )

            return job_data
        return None

    def complete_job(self, job_id: str,
                     result_data: Dict[str, Any] = None):
        """Mark a job as completed."""
        self.redis.srem(self.processing_set, job_id)

        # Get current job data
        job_json = self.redis.get(f"job:{job_id}")
        if job_json:
            job_data = json.loads(job_json)
            job_data["status"] = "completed"
            job_data["completed_at"] = datetime.now(timezone.utc).isoformat()
            if result_data:
                job_data["result"] = result_data

            # Update with shorter expiration (1 hour)
            self.redis.setex(f"job:{job_id}", 3600, json.dumps(job_data))

    def fail_job(self, job_id: str, error_message: str,
                 retry: bool = True):
        """Mark a job as failed and optionally retry."""
        self.redis.srem(self.processing_set, job_id)

        # Get current job data
        job_json = self.redis.get(f"job:{job_id}")
        if not job_json:
            return

        job_data = json.loads(job_json)
        job_data["attempts"] += 1
        job_data["last_error"] = error_message
        job_data["failed_at"] = datetime.now(timezone.utc).isoformat()

        if retry and job_data["attempts"] < job_data["max_attempts"]:
            # Retry: put back in queue
            job_data["status"] = "queued"
            self.redis.lpush(self.queue_name, json.dumps(job_data))
        else:
            # Max attempts reached
            job_data["status"] = "failed"

        self.redis.setex(f"job:{job_id}", 3600, json.dumps(job_data))

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a job."""
        job_json = self.redis.get(f"job:{job_id}")
        if job_json:
            return json.loads(job_json)
        return None

    def get_queue_length(self) -> int:
        """Get the current queue length."""
        return self.redis.llen(self.queue_name)

    def get_processing_count(self) -> int:
        """Get the number of jobs currently being processed."""
        return self.redis.scard(self.processing_set)
