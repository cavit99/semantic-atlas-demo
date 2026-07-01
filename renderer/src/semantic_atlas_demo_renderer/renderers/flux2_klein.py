from __future__ import annotations

import base64
import io
import os
import time
from pathlib import Path
from typing import Any

from PIL import Image

from semantic_atlas_demo_renderer.ideas import prompt_set_for_idea
from semantic_atlas_demo_renderer.interpolation import (
    EncodedPromptSet,
    InterpolationSettings,
    interpolate_conditioning,
)
from semantic_atlas_demo_renderer.schemas import Idea, PromptSetText, RenderedImage

from .base import Renderer

DEFAULT_KLEIN_4B_MODEL_PATH = (
    Path.home() / "ComfyUI/models/diffusion_models/flux-2-klein-4b.safetensors"
)
DEFAULT_QWEN_4B_MODEL_DIR = Path.home() / ".cache/semantic-atlas-demo/qwen3-4b"
QWEN3_OUTPUT_LAYERS = (9, 18, 27)
QWEN3_MAX_LENGTH = 512


class LocalQwen3Embedder:
    def __init__(self, model_spec: str | Path, device: Any) -> None:
        import torch
        from einops import rearrange
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        self.rearrange = rearrange
        self.device = device
        dtype = torch.float16 if torch.device(device).type == "mps" else torch.bfloat16
        self.model = AutoModel.from_pretrained(str(model_spec), dtype=dtype).to(device)
        self.tokenizer = AutoTokenizer.from_pretrained(str(model_spec))

    def eval(self) -> LocalQwen3Embedder:
        self.model.eval()
        return self

    def __call__(self, txt: list[str]):
        return self.forward(txt)

    def forward(self, txt: list[str]):
        torch = self.torch
        all_input_ids = []
        all_attention_masks = []

        for prompt in txt:
            text = self.tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            model_inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding="max_length",
                truncation=True,
                max_length=QWEN3_MAX_LENGTH,
            )
            all_input_ids.append(model_inputs["input_ids"])
            all_attention_masks.append(model_inputs["attention_mask"])

        with torch.no_grad():
            output = self.model(
                input_ids=torch.cat(all_input_ids, dim=0).to(self.device),
                attention_mask=torch.cat(all_attention_masks, dim=0).to(self.device),
                output_hidden_states=True,
                use_cache=False,
            )

        out = torch.stack([output.hidden_states[k] for k in QWEN3_OUTPUT_LAYERS], dim=1)
        return self.rearrange(out, "b c l d -> b l (c d)")


class Flux2KleinRenderer(Renderer):
    name = "flux2-klein-4b"

    def __init__(self) -> None:
        try:
            import torch
            from flux2.util import load_ae, load_flow_model, load_text_encoder
        except Exception as error:  # pragma: no cover - optional model path
            raise RuntimeError(
                "flux2_klein requires the BFL flux2 package and PyTorch. "
                "Run `uv sync --group local-models` in renderer/ before using this backend."
            ) from error

        configure_local_flux2_paths()
        self.torch = torch
        self.model_name = os.environ.get("FLUX2_MODEL_NAME", "flux.2-klein-4b")
        self.device = resolve_device(
            torch,
            os.environ.get("DEVICE", os.environ.get("ATLAS_RENDERER_DEVICE", "auto")),
        )
        self.grid_batch_size = resolve_grid_batch_size(self.device)

        self.settings = InterpolationSettings(
            step_scale=float(os.environ.get("ATLAS_STEP_SCALE", "1.0")),
            x_gain=float(os.environ.get("ATLAS_X_GAIN", "1.35")),
            y_gain=float(os.environ.get("ATLAS_Y_GAIN", "1.35")),
            edge_start=float(os.environ.get("ATLAS_EDGE_START", "0.35")),
            edge_boost=float(os.environ.get("ATLAS_EDGE_BOOST", "1.25")),
        )
        self.encoded_by_idea: dict[str, EncodedPromptSet] = {}

        self.text_encoder = self._load_text_encoder(load_text_encoder)
        self.model = load_flow_model(self.model_name, device=self.device)
        self.ae = load_ae(self.model_name, device=self.device)
        self.text_encoder.eval()
        self.model.eval()
        self.ae.eval()

    async def render(
        self,
        *,
        idea: Idea,
        x: float,
        y: float,
        world_seed: int,
        width: int,
        height: int,
    ) -> RenderedImage:
        if width % 16 != 0 or height % 16 != 0:
            raise ValueError("width and height must be multiples of 16 for Flux2")

        start = time.perf_counter()
        torch = self.torch
        encoded = self._encoded_prompt_set(idea)
        with torch.inference_mode():
            ctx = interpolate_conditioning(
                encoded,
                x=x,
                y=y,
                settings=self.settings,
            ).to(dtype=torch.bfloat16, device=self.device)
            image = self._sample(ctx=ctx, width=width, height=height, seed=world_seed)

        buffer = io.BytesIO()
        image.save(buffer, format="WEBP", quality=90)
        encoded_image = base64.b64encode(buffer.getvalue()).decode("ascii")
        return RenderedImage(
            imageUrl=f"data:image/webp;base64,{encoded_image}",
            width=width,
            height=height,
            x=x,
            y=y,
            seed=world_seed,
            elapsedMs=int((time.perf_counter() - start) * 1000),
            backend=self.name,
        )

    async def render_many(
        self,
        *,
        idea: Idea,
        points: list[dict[str, Any]],
        world_seed: int,
        width: int,
        height: int,
    ) -> list[RenderedImage]:
        if not points:
            return []
        if len(points) == 1:
            point = points[0]
            return [
                await self.render(
                    idea=idea,
                    x=float(point["x"]),
                    y=float(point["y"]),
                    world_seed=world_seed,
                    width=width,
                    height=height,
                )
            ]
        if width % 16 != 0 or height % 16 != 0:
            raise ValueError("width and height must be multiples of 16 for Flux2")

        try:
            return self._render_many_sync(
                idea=idea,
                points=points,
                world_seed=world_seed,
                width=width,
                height=height,
            )
        except RuntimeError as error:
            if not is_memory_error(error):
                raise
            self._clear_device_cache()
            rendered: list[RenderedImage] = []
            for point in points:
                rendered.extend(
                    await self.render_many(
                        idea=idea,
                        points=[point],
                        world_seed=world_seed,
                        width=width,
                        height=height,
                    )
                )
            return rendered

    def _render_many_sync(
        self,
        *,
        idea: Idea,
        points: list[dict[str, Any]],
        world_seed: int,
        width: int,
        height: int,
    ) -> list[RenderedImage]:
        started = time.perf_counter()
        torch = self.torch
        encoded = self._encoded_prompt_set(idea)
        with torch.inference_mode():
            ctx = torch.cat(
                [
                    interpolate_conditioning(
                        encoded,
                        x=float(point["x"]),
                        y=float(point["y"]),
                        settings=self.settings,
                    )
                    for point in points
                ],
                dim=0,
            ).to(dtype=torch.bfloat16, device=self.device)
            images = self._sample_batch(
                ctx=ctx,
                width=width,
                height=height,
                seeds=[world_seed for _point in points],
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return [
            RenderedImage(
                imageUrl=image_to_data_uri(image),
                width=width,
                height=height,
                x=float(point["x"]),
                y=float(point["y"]),
                seed=world_seed,
                elapsedMs=elapsed_ms,
                backend=self.name,
            )
            for point, image in zip(points, images, strict=True)
        ]

    def _encoded_prompt_set(self, idea: Idea) -> EncodedPromptSet:
        existing = self.encoded_by_idea.get(idea.id)
        if existing is not None:
            return existing
        encoded = self._encode_prompt_set(prompt_set_for_idea(idea))
        self.encoded_by_idea[idea.id] = encoded
        return encoded

    def _load_text_encoder(self, load_text_encoder: Any) -> Any:
        model_spec = os.environ.get("FLUX2_TEXT_ENCODER_MODEL")
        if model_spec:
            model_path = Path(model_spec).expanduser()
            if model_path.exists() and model_path.is_file():
                raise RuntimeError(
                    "FLUX2_TEXT_ENCODER_MODEL must point to a Transformers model directory or repo id. "
                    "A single qwen_3_4b.safetensors file is not enough because tokenizer/config files are also needed."
                )
            if model_path.exists():
                return LocalQwen3Embedder(model_path, device=self.device)

            from flux2.text_encoder import Qwen3Embedder

            return Qwen3Embedder(model_spec=model_spec, device=self.device)

        if DEFAULT_QWEN_4B_MODEL_DIR.exists():
            return LocalQwen3Embedder(DEFAULT_QWEN_4B_MODEL_DIR, device=self.device)

        return load_text_encoder(self.model_name, device=self.device)

    def _encode_prompt_set(self, prompt_set: PromptSetText) -> EncodedPromptSet:
        torch = self.torch
        fields: list[tuple[str, str | None]] = [
            ("base", prompt_set.base),
            ("x_negative", prompt_set.x_negative),
            ("x_positive", prompt_set.x_positive),
            ("y_negative", prompt_set.y_negative),
            ("y_positive", prompt_set.y_positive),
            ("x_negative_extreme", prompt_set.x_negative_extreme),
            ("x_positive_extreme", prompt_set.x_positive_extreme),
            ("y_negative_extreme", prompt_set.y_negative_extreme),
            ("y_positive_extreme", prompt_set.y_positive_extreme),
        ]
        active = [(name, value) for name, value in fields if value]
        with torch.inference_mode():
            encoded = self.text_encoder([value for _, value in active]).to(
                dtype=torch.bfloat16,
                device=self.device,
            )
        by_name = {name: encoded[index : index + 1] for index, (name, _value) in enumerate(active)}
        return EncodedPromptSet(
            base=by_name["base"],
            x_negative=by_name["x_negative"],
            x_positive=by_name["x_positive"],
            y_negative=by_name["y_negative"],
            y_positive=by_name["y_positive"],
            x_negative_extreme=by_name.get("x_negative_extreme"),
            x_positive_extreme=by_name.get("x_positive_extreme"),
            y_negative_extreme=by_name.get("y_negative_extreme"),
            y_positive_extreme=by_name.get("y_positive_extreme"),
        )

    def _sample(self, *, ctx: Any, width: int, height: int, seed: int) -> Image.Image:
        return self._sample_batch(ctx=ctx, width=width, height=height, seeds=[seed])[0]

    def _sample_batch(
        self,
        *,
        ctx: Any,
        width: int,
        height: int,
        seeds: list[int],
    ) -> list[Image.Image]:
        import torch
        from einops import rearrange
        from flux2.sampling import (
            batched_prc_img,
            batched_prc_txt,
            denoise,
            get_schedule,
            scatter_ids,
        )

        ctx, ctx_ids = batched_prc_txt(ctx)
        shape = (1, 128, height // 16, width // 16)
        noise = torch.cat(
            [
                torch.randn(
                    shape,
                    generator=torch.Generator(device=self.device).manual_seed(seed),
                    dtype=torch.bfloat16,
                    device=self.device,
                )
                for seed in seeds
            ],
            dim=0,
        )
        x, x_ids = batched_prc_img(noise)
        timesteps = get_schedule(4, x.shape[1])
        x = denoise(
            self.model,
            x,
            x_ids,
            ctx,
            ctx_ids,
            timesteps=timesteps,
            guidance=1.0,
            img_cond_seq=None,
            img_cond_seq_ids=None,
        )
        x = torch.cat(scatter_ids(x, x_ids)).squeeze(2)
        decoded = self.ae.decode(x).float().clamp(-1, 1)
        images: list[Image.Image] = []
        for item in decoded:
            item = rearrange(item, "c h w -> h w c")
            images.append(Image.fromarray((127.5 * (item + 1.0)).cpu().byte().numpy()))
        return images

    def _clear_device_cache(self) -> None:
        torch = self.torch
        device_type = self.device.type
        if device_type == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif device_type == "mps" and hasattr(torch, "mps"):
            torch.mps.empty_cache()


def configure_local_flux2_paths() -> None:
    prefer_local_file_env("KLEIN_4B_MODEL_PATH", DEFAULT_KLEIN_4B_MODEL_PATH)


def prefer_local_file_env(name: str, fallback_path: Path) -> None:
    if name in os.environ:
        return
    if fallback_path.exists():
        os.environ[name] = str(fallback_path)


def resolve_device(torch: Any, requested: str):
    if requested != "auto":
        device = torch.device(requested)
        if device.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("DEVICE=cuda was requested, but CUDA is not available.")
        if device.type == "mps" and not torch.backends.mps.is_available():
            raise RuntimeError("DEVICE=mps was requested, but MPS is not available.")
        return device

    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def resolve_grid_batch_size(device: Any) -> int:
    configured = os.environ.get("ATLAS_GRID_BATCH_SIZE")
    if configured:
        return max(1, int(configured))
    device_type = getattr(device, "type", str(device))
    if device_type == "cuda":
        return 4
    if device_type == "mps":
        return 2
    return 1


def is_memory_error(error: RuntimeError) -> bool:
    message = str(error).lower()
    return "out of memory" in message or "mps backend out of memory" in message


def image_to_data_uri(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=90)
    encoded_image = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/webp;base64,{encoded_image}"
