from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import AsyncIterator
from typing import TypeVar

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .ideas import get_idea, load_ideas
from .jobs import JobStore
from .renderers.factory import create_renderer
from .schemas import CoordinateRequest, GridRequest, GridStartResponse, Idea

app = FastAPI(title="Semantic Atlas Demo Renderer")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

renderer = create_renderer()
jobs = JobStore()
T = TypeVar("T")


@app.get("/health")
async def health() -> dict[str, object]:
    return {"ok": True, "backend": renderer.name}


@app.get("/ideas")
async def ideas() -> dict[str, object]:
    return {"ideas": [idea.model_dump() for idea in load_ideas()]}


@app.post("/grid", response_model=GridStartResponse)
async def start_grid(request: GridRequest) -> GridStartResponse:
    try:
        idea = idea_for_request(get_idea(request.ideaId), request)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown idea '{request.ideaId}'") from error

    job = jobs.create(renderer.name)
    first_batch = chunks(render_order(request.gridSize), request.batchSize)[0]
    asyncio.create_task(render_grid_job(job.id, idea, request))
    return GridStartResponse(
        jobId=job.id,
        backend=renderer.name,
        initialBatchSize=len(first_batch),
        initialIndices=[cell["index"] for cell in first_batch],
    )


@app.get("/grid/{job_id}/events")
async def grid_events(job_id: str) -> StreamingResponse:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"unknown job '{job_id}'")
    return StreamingResponse(event_stream(job_id), media_type="text/event-stream")


@app.post("/render-coordinate")
async def render_coordinate(request: CoordinateRequest) -> dict[str, object]:
    try:
        idea = idea_for_request(get_idea(request.ideaId), request)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown idea '{request.ideaId}'") from error

    image = await renderer.render(
        idea=idea,
        x=request.x,
        y=request.y,
        world_seed=request.worldSeed,
        width=request.width,
        height=request.height,
    )
    return image.model_dump()


async def render_grid_job(job_id: str, idea, request: GridRequest) -> None:
    job = jobs.get(job_id)
    if not job:
        return
    started = time.perf_counter()
    try:
        total = request.gridSize * request.gridSize
        for batch in chunks(render_order(request.gridSize), request.batchSize):
            await job.publish(
                {
                    "type": "progress",
                    "jobId": job_id,
                    "phase": "rendering",
                    "completed": len([event for event in job.events if event.get("type") == "cell"]),
                    "total": total,
                    "batchSize": len(batch),
                    "indices": [cell["index"] for cell in batch],
                    "elapsedMs": int((time.perf_counter() - started) * 1000),
                    "backend": renderer.name,
                }
            )
            await asyncio.sleep(0.05)
            images = await renderer.render_many(
                idea=idea,
                points=batch,
                world_seed=request.worldSeed,
                width=request.width,
                height=request.height,
            )
            for cell, image in zip(batch, images, strict=True):
                await job.publish(
                    {
                        "type": "cell",
                        "jobId": job_id,
                        "index": cell["index"],
                        "row": cell["row"],
                        "col": cell["col"],
                        "x": cell["x"],
                        "y": cell["y"],
                        "imageUrl": image.imageUrl,
                        "elapsedMs": int((time.perf_counter() - started) * 1000),
                        "backend": renderer.name,
                    }
                )
            await asyncio.sleep(0.05)
        await job.finish(
            {
                "type": "done",
                "jobId": job_id,
                "elapsedMs": int((time.perf_counter() - started) * 1000),
                "backend": renderer.name,
            }
        )
    except Exception as error:
        await job.finish({"type": "error", "jobId": job_id, "message": str(error)})


async def event_stream(job_id: str) -> AsyncIterator[str]:
    job = jobs.get(job_id)
    if not job:
        return

    index = 0
    while True:
        payloads: list[str] = []
        should_break = False
        async with job.condition:
            while index >= len(job.events) and not job.done:
                await job.condition.wait()
            while index < len(job.events):
                event = job.events[index]
                index += 1
                payloads.append(f"data: {json.dumps(event)}\n\n")
            if job.done:
                should_break = True
        for payload in payloads:
            yield payload
        if should_break:
            break


def render_order(grid_size: int) -> list[dict[str, int | float]]:
    center = (grid_size - 1) / 2
    cells = [
        {
            "index": row * grid_size + col,
            "row": row,
            "col": col,
            "x": -1 + (2 * col / (grid_size - 1)),
            "y": 1 - (2 * row / (grid_size - 1)),
        }
        for row in range(grid_size)
        for col in range(grid_size)
    ]
    return sorted(
        cells,
        key=lambda cell: (
            abs(float(cell["row"]) - center) + abs(float(cell["col"]) - center),
            abs(float(cell["row"]) - center),
            abs(float(cell["col"]) - center),
            int(cell["index"]),
        ),
    )


def chunks(items: list[T], size: int) -> list[list[T]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def idea_for_request(idea: Idea, request: GridRequest | CoordinateRequest) -> Idea:
    updates = {}
    if request.xAxis is not None:
        updates["xAxis"] = request.xAxis
    if request.yAxis is not None:
        updates["yAxis"] = request.yAxis
    if not updates:
        return idea
    return idea.model_copy(update=updates)


def main() -> None:
    uvicorn.run(
        "semantic_atlas_demo_renderer.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8791")),
        reload=os.environ.get("RELOAD", "1") == "1",
    )


if __name__ == "__main__":
    main()
