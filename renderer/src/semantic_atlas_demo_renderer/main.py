from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import AsyncIterator

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .ideas import get_idea, load_ideas
from .jobs import JobStore
from .renderers.factory import create_renderer
from .schemas import CoordinateRequest, GridRequest, GridStartResponse

app = FastAPI(title="Semantic Atlas Demo Renderer")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

renderer = create_renderer()
jobs = JobStore()


@app.get("/health")
async def health() -> dict[str, object]:
    return {"ok": True, "backend": renderer.name}


@app.get("/ideas")
async def ideas() -> dict[str, object]:
    return {"ideas": [idea.model_dump() for idea in load_ideas()]}


@app.post("/grid", response_model=GridStartResponse)
async def start_grid(request: GridRequest) -> GridStartResponse:
    try:
        idea = get_idea(request.ideaId)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown idea '{request.ideaId}'") from error

    job = jobs.create(renderer.name)
    asyncio.create_task(render_grid_job(job.id, idea, request))
    return GridStartResponse(jobId=job.id, backend=renderer.name)


@app.get("/grid/{job_id}/events")
async def grid_events(job_id: str) -> StreamingResponse:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"unknown job '{job_id}'")
    return StreamingResponse(event_stream(job_id), media_type="text/event-stream")


@app.post("/render-coordinate")
async def render_coordinate(request: CoordinateRequest) -> dict[str, object]:
    try:
        idea = get_idea(request.ideaId)
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
        for cell in render_order():
            image = await renderer.render(
                idea=idea,
                x=cell["x"],
                y=cell["y"],
                world_seed=request.worldSeed,
                width=request.width,
                height=request.height,
            )
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


def render_order() -> list[dict[str, int]]:
    cells = [
        {"index": 0, "row": 0, "col": 0, "x": -1, "y": 1},
        {"index": 1, "row": 0, "col": 1, "x": 0, "y": 1},
        {"index": 2, "row": 0, "col": 2, "x": 1, "y": 1},
        {"index": 3, "row": 1, "col": 0, "x": -1, "y": 0},
        {"index": 4, "row": 1, "col": 1, "x": 0, "y": 0},
        {"index": 5, "row": 1, "col": 2, "x": 1, "y": 0},
        {"index": 6, "row": 2, "col": 0, "x": -1, "y": -1},
        {"index": 7, "row": 2, "col": 1, "x": 0, "y": -1},
        {"index": 8, "row": 2, "col": 2, "x": 1, "y": -1},
    ]
    order = [4, 3, 5, 1, 7, 0, 2, 6, 8]
    by_index = {cell["index"]: cell for cell in cells}
    return [by_index[index] for index in order]


def main() -> None:
    uvicorn.run(
        "semantic_atlas_demo_renderer.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8791")),
        reload=os.environ.get("RELOAD", "1") == "1",
    )


if __name__ == "__main__":
    main()
