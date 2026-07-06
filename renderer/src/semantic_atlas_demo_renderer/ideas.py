from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .schemas import Idea, PromptSetText

DEFAULT_STYLE_ANCHOR = "consistent non-photographic illustrated concept art, hand-rendered surface, no camera realism"


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


def compose_endpoint_prompt(midpoint_prompt: str, transform_prompt: str | None, suffix: str) -> str:
    parts = [
        midpoint_prompt.strip(),
        transform_prompt.strip() if transform_prompt else "",
        DEFAULT_STYLE_ANCHOR,
        suffix.strip(),
    ]
    return ", ".join(part for part in parts if part)


def prompt_set_for_idea(idea: Idea) -> PromptSetText:
    return PromptSetText(
        base=compose_endpoint_prompt(idea.midpointPrompt, None, idea.suffix),
        x_negative=compose_endpoint_prompt(idea.midpointPrompt, idea.xAxis.negativePrompt, idea.suffix),
        x_positive=compose_endpoint_prompt(idea.midpointPrompt, idea.xAxis.positivePrompt, idea.suffix),
        y_negative=compose_endpoint_prompt(idea.midpointPrompt, idea.yAxis.negativePrompt, idea.suffix),
        y_positive=compose_endpoint_prompt(idea.midpointPrompt, idea.yAxis.positivePrompt, idea.suffix),
    )
