from __future__ import annotations

import pytest

from semantic_atlas_demo_renderer.renderers.factory import create_renderer
from semantic_atlas_demo_renderer.renderers.mock import MockRenderer


def test_default_backend_is_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENDER_BACKEND", raising=False)

    assert isinstance(create_renderer(), MockRenderer)


def test_auto_backend_is_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDER_BACKEND", "auto")

    assert isinstance(create_renderer(), MockRenderer)


def test_sdxl_backend_is_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDER_BACKEND", "sdxl_mps")

    with pytest.raises(ValueError, match="unknown RENDER_BACKEND 'sdxl_mps'"):
        create_renderer()
