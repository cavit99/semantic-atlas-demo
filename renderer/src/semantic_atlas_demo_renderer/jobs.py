from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class GridJob:
    id: str
    backend: str
    started_at: float = field(default_factory=time.perf_counter)
    events: list[dict[str, Any]] = field(default_factory=list)
    done: bool = False
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)

    async def publish(self, event: dict[str, Any]) -> None:
        async with self.condition:
            self.events.append(event)
            self.condition.notify_all()

    async def finish(self, event: dict[str, Any]) -> None:
        async with self.condition:
            self.events.append(event)
            self.done = True
            self.condition.notify_all()


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, GridJob] = {}

    def create(self, backend: str) -> GridJob:
        job = GridJob(id=uuid4().hex, backend=backend)
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> GridJob | None:
        return self._jobs.get(job_id)
