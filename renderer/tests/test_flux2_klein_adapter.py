from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from semantic_atlas_demo_renderer.ideas import DEFAULT_STYLE_ANCHOR, compose_prompt, load_ideas, prompt_set_for_idea
from semantic_atlas_demo_renderer.interpolation import EncodedPromptSet, InterpolationSettings
from semantic_atlas_demo_renderer.renderers import flux2_klein
from semantic_atlas_demo_renderer.renderers.flux2_klein import Flux2KleinRenderer

from .test_interpolation import FakeTensor


class FakeTorch:
    bfloat16 = "bf16"

    def inference_mode(self) -> contextlib.AbstractContextManager[None]:
        return contextlib.nullcontext()


def test_prompt_set_for_idea_builds_base_and_axis_endpoint_prompts() -> None:
    idea = load_ideas()[0]
    prompt_set = prompt_set_for_idea(idea)

    assert DEFAULT_STYLE_ANCHOR in prompt_set.base
    assert idea.xAxis.negativePrompt not in prompt_set.base
    assert idea.yAxis.positivePrompt not in prompt_set.base
    assert idea.xAxis.negativePrompt in prompt_set.x_negative
    assert idea.xAxis.positivePrompt in prompt_set.x_positive
    assert idea.yAxis.negativePrompt in prompt_set.y_negative
    assert idea.yAxis.positivePrompt in prompt_set.y_positive


def test_compose_prompt_uses_image_language_without_axis_metadata() -> None:
    idea = load_ideas()[0]

    center = compose_prompt(idea, x=0.0, y=0.0)
    assert idea.xAxis.positivePrompt not in center
    assert idea.yAxis.positivePrompt not in center
    assert "axis" not in center.lower()

    corner = compose_prompt(idea, x=0.5, y=-1.0)
    assert f"moderate {idea.xAxis.positivePrompt}" in corner
    assert f"strong {idea.yAxis.negativePrompt}" in corner
    assert "axis" not in corner.lower()
    assert "grid" not in corner.lower()


def test_text_encoder_override_rejects_single_safetensors_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    qwen_file = tmp_path / "qwen_3_4b.safetensors"
    qwen_file.write_bytes(b"stub")
    monkeypatch.setenv("FLUX2_TEXT_ENCODER_MODEL", str(qwen_file))

    renderer = Flux2KleinRenderer.__new__(Flux2KleinRenderer)
    renderer.device = "test-device"

    with pytest.raises(RuntimeError, match="single qwen_3_4b.safetensors"):
        renderer._load_text_encoder(lambda *_args, **_kwargs: object())


def test_text_encoder_override_uses_local_transformers_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("FLUX2_TEXT_ENCODER_MODEL", str(tmp_path))
    calls: list[dict[str, object]] = []

    class FakeLocalQwen3Embedder:
        def __init__(self, model_spec: Path, device: object) -> None:
            calls.append({"model_spec": model_spec, "device": device})

    monkeypatch.setattr(flux2_klein, "LocalQwen3Embedder", FakeLocalQwen3Embedder)

    renderer = Flux2KleinRenderer.__new__(Flux2KleinRenderer)
    renderer.device = "test-device"
    embedder = renderer._load_text_encoder(lambda *_args, **_kwargs: object())

    assert isinstance(embedder, FakeLocalQwen3Embedder)
    assert calls == [{"model_spec": tmp_path, "device": "test-device"}]


def test_text_encoder_without_override_uses_flux2_loader_on_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLUX2_TEXT_ENCODER_MODEL", raising=False)

    renderer = Flux2KleinRenderer.__new__(Flux2KleinRenderer)
    renderer.device = SimpleNamespace(type="cuda")
    renderer.model_name = "flux.2-klein-4b"

    def fake_loader(model_name: str, *, device: object) -> dict[str, object]:
        return {"model_name": model_name, "device": device}

    assert renderer._load_text_encoder(fake_loader) == {
        "model_name": "flux.2-klein-4b",
        "device": renderer.device,
    }


def test_text_encoder_without_override_uses_non_fp8_qwen_on_mps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLUX2_TEXT_ENCODER_MODEL", raising=False)

    renderer = Flux2KleinRenderer.__new__(Flux2KleinRenderer)
    renderer.device = SimpleNamespace(type="mps")
    renderer.model_name = "flux.2-klein-4b"

    def fake_qwen_loader(model_spec: str) -> dict[str, object]:
        return {"model_spec": model_spec, "device": renderer.device}

    def forbidden_flux_loader(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("MPS must not use the Flux2 default FP8 text encoder loader")

    monkeypatch.setattr(renderer, "_load_qwen3_embedder", fake_qwen_loader)

    assert renderer._load_text_encoder(forbidden_flux_loader) == {
        "model_spec": flux2_klein.MPS_SAFE_QWEN3_MODEL,
        "device": renderer.device,
    }


def test_flux2_klein_render_uses_interpolated_conditioning_before_sampling() -> None:
    idea = load_ideas()[0]
    encoded = EncodedPromptSet(
        base=FakeTensor(10.0),
        x_negative=FakeTensor(1.0),
        x_positive=FakeTensor(14.0),
        y_negative=FakeTensor(3.0),
        y_positive=FakeTensor(20.0),
    )
    sample_calls: list[dict[str, object]] = []

    renderer = Flux2KleinRenderer.__new__(Flux2KleinRenderer)
    renderer.torch = FakeTorch()
    renderer.device = "test-device"
    renderer.settings = InterpolationSettings()
    renderer._encoded_prompt_set = lambda _idea: encoded

    def fake_sample(*, ctx: FakeTensor, width: int, height: int, seed: int) -> Image.Image:
        sample_calls.append({"ctx": ctx, "width": width, "height": height, "seed": seed})
        return Image.new("RGB", (width, height), color=(0, 0, 0))

    renderer._sample = fake_sample

    rendered = asyncio.run(
        renderer.render(
            idea=idea,
            x=1.0,
            y=-1.0,
            world_seed=123,
            width=512,
            height=512,
        )
    )

    assert rendered.backend == renderer.name
    assert rendered.width == 512
    assert rendered.height == 512
    assert len(sample_calls) == 1
    assert sample_calls[0]["seed"] == 123
    assert sample_calls[0]["width"] == 512
    assert sample_calls[0]["height"] == 512
    ctx = sample_calls[0]["ctx"]
    assert isinstance(ctx, FakeTensor)
    assert ctx.value == 7.0
    assert ctx.to_calls == [{"dtype": "bf16", "device": "test-device"}]


def test_encoded_prompt_cache_key_changes_when_axes_change() -> None:
    idea = load_ideas()[0]
    changed = idea.model_copy(
        update={
            "xAxis": idea.xAxis.model_copy(
                update={
                    "negativeLabel": "matte",
                    "negativePrompt": "flat matte surfaces",
                }
            )
        }
    )

    assert flux2_klein.encoded_prompt_cache_key(idea) != flux2_klein.encoded_prompt_cache_key(changed)
