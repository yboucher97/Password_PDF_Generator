from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .utils import ensure_directory


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass(slots=True)
class JobRecord:
    job_id: str
    status: str
    created_at: str
    request_summary: dict[str, Any]
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "request_summary": self.request_summary,
            "error": self.error,
            "result": self.result,
        }


class JobStore:
    def __init__(self, jobs_dir: Path, logger) -> None:
        self.jobs_dir = ensure_directory(jobs_dir)
        self.logger = logger
        self._lock = threading.Lock()
        self._jobs: dict[str, JobRecord] = {}

    def create(self, job_id: str, request_summary: dict[str, Any]) -> JobRecord:
        record = JobRecord(
            job_id=job_id,
            status="queued",
            created_at=_utc_now(),
            request_summary=request_summary,
        )
        with self._lock:
            self._jobs[job_id] = record
            self._write(record)
        return record

    def mark_running(self, job_id: str) -> None:
        with self._lock:
            record = self._require(job_id)
            record.status = "running"
            record.started_at = _utc_now()
            self._write(record)

    def mark_succeeded(self, job_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            record = self._require(job_id)
            record.status = "completed"
            record.finished_at = _utc_now()
            record.result = result
            record.error = None
            self._write(record)

    def mark_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            record = self._require(job_id)
            if record.started_at is None:
                record.started_at = _utc_now()
            record.status = "failed"
            record.finished_at = _utc_now()
            record.error = error
            self._write(record)

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is not None:
                return record.to_dict()

        path = self.jobs_dir / f"{job_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _require(self, job_id: str) -> JobRecord:
        record = self._jobs.get(job_id)
        if record is None:
            raise KeyError(f"Unknown job id: {job_id}")
        return record

    def _write(self, record: JobRecord) -> None:
        path = self.jobs_dir / f"{record.job_id}.json"
        path.write_text(json.dumps(record.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
