from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .schemas import Idea


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def load_ideas() -> list[Idea]:
    raw = (repo_root() / "data" / "ideas.json").read_text()
    return [Idea.model_validate(item) for item in json.loads(raw)]


def get_idea(idea_id: str) -> Idea:
    for idea in load_ideas():
        if idea.id == idea_id:
            return idea
    raise KeyError(idea_id)


def compose_prompt(idea: Idea, x: float, y: float) -> str:
    x_prompt = idea.xAxis.positivePrompt if x >= 0 else idea.xAxis.negativePrompt
    y_prompt = idea.yAxis.positivePrompt if y >= 0 else idea.yAxis.negativePrompt
    x_weight = abs(x)
    y_weight = abs(y)
    parts = [
        idea.midpointPrompt,
        f"x-axis influence {x_weight:.2f}: {x_prompt}",
        f"y-axis influence {y_weight:.2f}: {y_prompt}",
        idea.suffix,
    ]
    return ", ".join(part.strip() for part in parts if part.strip())
