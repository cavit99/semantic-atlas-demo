from __future__ import annotations

import os

from .base import Renderer
from .flux2_klein import Flux2KleinRenderer
from .mock import MockRenderer


def create_renderer() -> Renderer:
    backend = os.environ.get("RENDER_BACKEND", "mock").lower()
    if backend in {"mock", "auto"}:
        return MockRenderer()
    if backend == "flux2_klein":
        return Flux2KleinRenderer()
    raise ValueError(f"unknown RENDER_BACKEND '{backend}'")
