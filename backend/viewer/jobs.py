"""
Background blink jobs: a thread pool (at most 2 running) and an in-memory dict of jobs (COMMON §6).

A cold blink takes 1–2 minutes, so the view answers 202 at once and the frontend polls the status.
Jobs are lost on restart, which is fine: finished results are in the file cache.
The server must run as ONE process (threads are fine), otherwise a status poll can miss its job.
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable

from core.blink import BlinkError

log = logging.getLogger(__name__)

# CLAUDE.md: ≤ 2 jobs at a time (each one already opens up to 4 IRSA downloads); 1 on a small server
MAX_RUNNING = max(1, min(2, int(os.environ.get("SKYBLINK_MAX_JOBS", "2"))))
# SKYBLINK_ALLOW_COLD=0: never download from IRSA on this server; presets and cached results still work
ALLOW_COLD = os.environ.get("SKYBLINK_ALLOW_COLD", "1") != "0"
MAX_ACTIVE = 8       # queued + running; above this the API answers 429 instead of piling up work
JOB_TTL_S = 3600     # finished jobs are forgotten after an hour

Progress = Callable[[str, float], None]


class QueueFull(Exception):
    pass


@dataclass
class Job:
    id: str
    key: str
    status: str = "queued"          # queued | running | done | error
    progress: float = 0.0
    stage: str = "queued"
    result: dict | None = None
    error_code: str | None = None
    finished_at: float | None = field(default=None, repr=False)

    def payload(self) -> dict:
        d = {"job_id": self.id, "status": self.status, "progress": round(self.progress, 3), "stage": self.stage}
        if self.status == "done":
            d["result"] = self.result
        if self.status == "error":
            d["error_code"] = self.error_code
        return d


_executor = ThreadPoolExecutor(max_workers=MAX_RUNNING, thread_name_prefix="blink")
_lock = threading.Lock()
_jobs: dict[str, Job] = {}
_active_by_key: dict[str, str] = {}


def _prune(now: float) -> None:
    for jid in [j.id for j in _jobs.values() if j.finished_at and now - j.finished_at > JOB_TTL_S]:
        del _jobs[jid]


class ColdDisabled(Exception):
    pass


def submit(key: str, work: Callable[[Progress], dict]) -> Job:
    """Queue `work` unless the same request is already queued or running; then return that job."""
    if not ALLOW_COLD:
        raise ColdDisabled
    with _lock:
        _prune(time.time())
        jid = _active_by_key.get(key)
        if jid:
            return _jobs[jid]
        if len(_active_by_key) >= MAX_ACTIVE:
            raise QueueFull
        job = Job(id=uuid.uuid4().hex, key=key)
        _jobs[job.id] = job
        _active_by_key[key] = job.id
    _executor.submit(_run, job, work)
    return job


def get(job_id: str) -> Job | None:
    with _lock:
        return _jobs.get(job_id)


def _run(job: Job, work: Callable[[Progress], dict]) -> None:
    def progress(stage: str, fraction: float) -> None:
        job.stage, job.progress = stage, max(job.progress, min(float(fraction), 1.0))

    job.status, job.stage = "running", "search"
    try:
        result = work(progress)
        job.result, job.progress, job.stage, job.status = result, 1.0, "done", "done"
    except BlinkError as e:
        log.warning("blink job %s failed: %s %s", job.id, e.code, e.detail)
        job.error_code, job.status = e.code, "error"
    except Exception:  # noqa: BLE001 — never leak a stack trace to the client (COMMON §16)
        log.exception("blink job %s crashed", job.id)
        job.error_code, job.status = "server_error", "error"
    finally:
        with _lock:
            job.finished_at = time.time()
            _active_by_key.pop(job.key, None)
