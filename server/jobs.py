"""Background job runner with progress reporting.

The pipeline has one genuinely slow stage: scoring, measured at roughly 45
seconds per 5-second clip. That cannot sit inside a blocking HTTP request, so
long stages run on a worker thread and the UI polls for progress.

Progress for scoring is derived by watching the score files appear in the run
directory. That keeps the reporting honest -- it reflects work actually
completed on disk -- and requires no change to the pipeline code itself.
"""
from __future__ import annotations

import threading
import time
import traceback
import uuid


class Job:
    def __init__(self, kind, total=None, label=""):
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.state = "running"        # running | done | error
        self.total = total
        self.done = 0
        self.label = label
        self.result = None
        self.error = None
        self.started = time.time()
        self.finished = None
        self.log = []

    def note(self, msg):
        self.log.append({"t": round(time.time() - self.started, 2), "msg": msg})

    def as_dict(self):
        pct = None
        if self.total:
            pct = round(100.0 * min(self.done, self.total) / self.total, 1)
        elif self.state == "done":
            pct = 100.0
        return {
            "id": self.id,
            "kind": self.kind,
            "state": self.state,
            "done": self.done,
            "total": self.total,
            "percent": pct,
            "label": self.label,
            "elapsed_s": round((self.finished or time.time()) - self.started, 1),
            "error": self.error,
            "log": self.log[-12:],
        }


class JobRegistry:
    def __init__(self):
        self._jobs = {}
        self._lock = threading.Lock()

    def create(self, kind, total=None, label=""):
        job = Job(kind, total=total, label=label)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id):
        with self._lock:
            return self._jobs.get(job_id)

    def run(self, job, fn, watcher=None):
        """Execute fn(job) on a worker thread.

        `watcher` is an optional callable taking the job; it is polled on a
        second thread to update progress from observable side effects (files
        landing on disk) while fn is still running.
        """
        def _watch():
            while job.state == "running":
                try:
                    watcher(job)
                except Exception:
                    pass
                time.sleep(0.7)

        def _target():
            try:
                if watcher:
                    threading.Thread(target=_watch, daemon=True).start()
                job.result = fn(job)
                job.state = "done"
                if job.total:
                    job.done = job.total
            except Exception as exc:
                job.state = "error"
                job.error = "%s: %s" % (type(exc).__name__, exc)
                job.note(traceback.format_exc().strip().splitlines()[-1])
            finally:
                job.finished = time.time()

        threading.Thread(target=_target, daemon=True).start()
        return job


REGISTRY = JobRegistry()
