from __future__ import annotations

import queue
import threading
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from .models import RenderSettings
from .pipeline_engine import run_render_pipeline
from .utils import ensure_dirs


@dataclass
class JobEvent:
    event: str
    payload: dict


@dataclass
class RenderJob:
    job_id: str
    created_at: str
    status: str = "queued"
    progress: int = 0
    message: str = "Queued"
    output_file: Optional[str] = None
    error: Optional[str] = None
    events: queue.Queue[JobEvent] = field(default_factory=queue.Queue)


class JobManager:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.uploads = workspace_root / "uploads"
        self.jobs_root = workspace_root / "jobs"
        self.outputs = workspace_root / "outputs"
        ensure_dirs([self.uploads, self.jobs_root, self.outputs])

        self._jobs: dict[str, RenderJob] = {}
        self._lock = threading.Lock()

    def create_job(self, settings: RenderSettings) -> RenderJob:
        job_id = uuid.uuid4().hex
        job = RenderJob(job_id=job_id, created_at=datetime.utcnow().isoformat() + "Z")

        with self._lock:
            self._jobs[job_id] = job

        thread = threading.Thread(
            target=self._run_job,
            args=(job, settings),
            daemon=True,
        )
        thread.start()
        return job

    def get_job(self, job_id: str) -> Optional[RenderJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def _emit(self, job: RenderJob, event: str, payload: dict) -> None:
        job.events.put(JobEvent(event=event, payload=payload))

    def _update_status(self, job: RenderJob, message: str, progress: int, status: Optional[str] = None) -> None:
        if status:
            job.status = status
        job.message = message
        job.progress = max(0, min(100, progress))
        self._emit(
            job,
            "progress",
            {
                "status": job.status,
                "message": job.message,
                "progress": job.progress,
                "output_file": job.output_file,
                "error": job.error,
            },
        )

    def _run_job(self, job: RenderJob, settings: RenderSettings) -> None:
        try:
            job.status = "running"
            self._update_status(job, "Starting render", 1, status="running")

            job_dir = self.jobs_root / job.job_id
            job_dir.mkdir(parents=True, exist_ok=True)

            output_path = run_render_pipeline(
                settings,
                job_dir,
                self.outputs,
                progress_callback=lambda msg, pct: self._update_status(job, msg, pct),
            )

            job.output_file = output_path.name
            self._update_status(job, "Render completed", 100, status="completed")
            self._emit(job, "done", {"job_id": job.job_id, "output_file": job.output_file})
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            self._update_status(job, "Render failed", job.progress or 100, status="failed")
            self._emit(
                job,
                "error",
                {
                    "job_id": job.job_id,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )

    def stream_events(self, job_id: str) -> Generator[JobEvent, None, None]:
        job = self.get_job(job_id)
        if not job:
            yield JobEvent("error", {"error": "Unknown job id"})
            return

        yield JobEvent(
            "progress",
            {
                "status": job.status,
                "message": job.message,
                "progress": job.progress,
                "output_file": job.output_file,
                "error": job.error,
            },
        )

        while True:
            try:
                event = job.events.get(timeout=20)
                yield event
                if event.event in {"done", "error"}:
                    break
            except queue.Empty:
                yield JobEvent(
                    "heartbeat",
                    {
                        "status": job.status,
                        "message": job.message,
                        "progress": job.progress,
                    },
                )
                if job.status in {"completed", "failed"}:
                    break
