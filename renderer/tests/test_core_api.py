from __future__ import annotations

import base64
import json
import os
import warnings
from collections.abc import Iterator

import pytest

os.environ["RENDER_BACKEND"] = "mock"
warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)

from fastapi.testclient import TestClient  # noqa: E402

from semantic_atlas_demo_renderer import main as renderer_main  # noqa: E402
from semantic_atlas_demo_renderer.ideas import load_ideas  # noqa: E402
from semantic_atlas_demo_renderer.jobs import JobStore  # noqa: E402
from semantic_atlas_demo_renderer.renderers.mock import MockRenderer  # noqa: E402


@pytest.fixture()
def client() -> Iterator[TestClient]:
    renderer = MockRenderer()
    renderer.grid_batch_size = 3
    renderer_main.renderer = renderer
    renderer_main.jobs = JobStore()
    with TestClient(renderer_main.app) as test_client:
        yield test_client


def test_demo_catalog_has_five_complete_unique_presets() -> None:
    ideas = load_ideas()
    ids = {idea.id for idea in ideas}

    assert len(ideas) == 5
    assert len(ids) == 5
    for idea in ideas:
        assert idea.title
        assert idea.midpointPrompt
        assert len(idea.palette) == 4
        assert idea.xAxis.negativeLabel
        assert idea.xAxis.positiveLabel
        assert idea.yAxis.negativeLabel
        assert idea.yAxis.positiveLabel


def test_health_and_ideas_endpoints(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"ok": True, "backend": "mock-live"}

    response = client.get("/ideas")
    assert response.status_code == 200
    payload = response.json()
    assert [idea["id"] for idea in payload["ideas"]] == [idea.id for idea in load_ideas()]


def test_render_coordinate_returns_webp_data_uri(client: TestClient) -> None:
    response = client.post(
        "/render-coordinate",
        json={
            "ideaId": "greenhouse-laboratory",
            "x": 1,
            "y": -1,
            "worldSeed": 123,
            "width": 256,
            "height": 256,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["backend"] == "mock-live"
    assert payload["width"] == 256
    assert payload["height"] == 256
    assert payload["x"] == 1
    assert payload["y"] == -1
    assert payload["imageUrl"].startswith("data:image/webp;base64,")

    encoded = payload["imageUrl"].split(",", 1)[1]
    assert base64.b64decode(encoded).startswith(b"RIFF")


def test_grid_job_streams_progress_cells_and_done(client: TestClient) -> None:
    response = client.post(
        "/grid",
        json={
            "ideaId": "greenhouse-laboratory",
            "gridSize": 3,
            "worldSeed": 123,
            "width": 256,
            "height": 256,
        },
    )
    assert response.status_code == 200
    job_id = response.json()["jobId"]

    with client.stream("GET", f"/grid/{job_id}/events") as stream:
        assert stream.status_code == 200
        events = parse_sse_events(stream.read().decode("utf-8"))

    progress_events = [event for event in events if event["type"] == "progress"]
    cell_events = [event for event in events if event["type"] == "cell"]
    done_events = [event for event in events if event["type"] == "done"]

    assert [event["batchSize"] for event in progress_events] == [3, 3, 3]
    assert len(cell_events) == 9
    assert {event["index"] for event in cell_events} == set(range(9))
    assert all(event["imageUrl"].startswith("data:image/webp;base64,") for event in cell_events)
    assert done_events == [
        {
            "type": "done",
            "jobId": job_id,
            "elapsedMs": done_events[0]["elapsedMs"],
            "backend": "mock-live",
        }
    ]
    assert events[-1]["type"] == "done"


def test_unknown_idea_returns_404(client: TestClient) -> None:
    response = client.post(
        "/render-coordinate",
        json={
            "ideaId": "missing",
            "x": 0,
            "y": 0,
            "worldSeed": 1,
            "width": 256,
            "height": 256,
        },
    )

    assert response.status_code == 404
    assert "unknown idea" in response.json()["detail"]


def parse_sse_events(body: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for block in body.strip().split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line.removeprefix("data: ")))
    return events
