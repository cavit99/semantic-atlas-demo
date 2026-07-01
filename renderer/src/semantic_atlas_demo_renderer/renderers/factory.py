from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from .base import Renderer
from .flux2_klein import Flux2KleinRenderer
from .mock import MockRenderer
from .sdxl_mps import SDXLMpsRenderer


def create_renderer() -> Renderer:
    backend = os.environ.get("RENDER_BACKEND", "auto").lower()
    if backend == "mock":
        return MockRenderer()
    if backend == "sdxl_mps":
        return SDXLMpsRenderer()
    if backend == "flux2_klein":
        return Flux2KleinRenderer()
    if backend != "auto":
        raise ValueError(f"unknown RENDER_BACKEND '{backend}'")

    if _has_module("diffusers") and _has_module("torch") and _has_sdxl_cache():
        try:
            return SDXLMpsRenderer()
        except RuntimeError:
            return MockRenderer()
    return MockRenderer()


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _has_sdxl_cache() -> bool:
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub" / "models--stabilityai--stable-diffusion-xl-base-1.0"
    return cache_dir.exists()
