from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from hashlib import sha256
from typing import Callable, Any
import json, threading, time

@dataclass
class JobState:
    job_id: str
    status: str = "queued"
    progress: float = 0.0
    result: Any = None
    error: str | None = None
    started_at: float | None = None
    finished_at: float | None = None
    checkpoint_key: str | None = None

class CheckpointStore:
    def __init__(self):
        self.data: dict[str, dict] = {}
        self.lock = threading.Lock()
    def save(self, key: str, payload: dict) -> None:
        with self.lock:
            self.data[key] = json.loads(json.dumps(payload, default=str))
    def load(self, key: str) -> dict | None:
        with self.lock:
            value = self.data.get(key)
            return json.loads(json.dumps(value, default=str)) if value is not None else None
    def delete(self, key: str) -> None:
        with self.lock:
            self.data.pop(key, None)

class ExperimentCoordinator:
    def __init__(self, workers: int = 1):
        self.pool = ThreadPoolExecutor(max_workers=max(1, workers))
        self.jobs: dict[str, JobState] = {}
        self.futures: dict[str, Future] = {}
        self.checkpoints = CheckpointStore()
        self.lock = threading.Lock()

    @staticmethod
    def deterministic_id(spec: dict) -> str:
        canonical = json.dumps(spec, sort_keys=True, default=str, separators=(",", ":"))
        return "EVL-" + sha256(canonical.encode()).hexdigest()[:8].upper()

    def submit(self, fn: Callable[..., Any], *args, checkpoint_key: str | None = None, **kwargs) -> str:
        identity = {"fn": getattr(fn, "__qualname__", getattr(fn, "__name__", "job")), "args": args, "kwargs": kwargs}
        job_id = self.deterministic_id(identity)
        with self.lock:
            if job_id in self.jobs:
                return job_id
            self.jobs[job_id] = JobState(job_id, "queued", 0.0, checkpoint_key=checkpoint_key)
            future = self.pool.submit(fn, *args, **kwargs)
            self.futures[job_id] = future
            self.jobs[job_id].status = "running"
            self.jobs[job_id].started_at = time.time()
            future.add_done_callback(lambda f, jid=job_id: self._done(jid, f))
        return job_id

    def _done(self, job_id: str, future: Future) -> None:
        state = self.jobs[job_id]
        state.finished_at = time.time()
        if future.cancelled():
            state.status = "cancelled"
            state.progress = 1.0
            return
        exc = future.exception()
        state.status = "failed" if exc else "completed"
        state.error = str(exc) if exc else None
        state.result = None if exc else future.result()
        state.progress = 1.0

    def update_progress(self, job_id: str, progress: float) -> None:
        if job_id in self.jobs:
            self.jobs[job_id].progress = min(1.0, max(0.0, float(progress)))

    def status(self, job_id: str) -> JobState | None:
        return self.jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        future = self.futures.get(job_id)
        if future is None:
            return False
        ok = future.cancel()
        if ok:
            self.jobs[job_id].status = "cancelled"
            self.jobs[job_id].finished_at = time.time()
        return ok

    def save_checkpoint(self, job_id: str, payload: dict) -> None:
        state = self.jobs[job_id]
        self.checkpoints.save(state.checkpoint_key or job_id, payload)

    def resume_checkpoint(self, job_id: str) -> dict | None:
        state = self.jobs.get(job_id)
        return None if state is None else self.checkpoints.load(state.checkpoint_key or job_id)

    def shutdown(self) -> None:
        self.pool.shutdown(wait=False, cancel_futures=True)
