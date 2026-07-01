from __future__ import annotations

import base64
import io
import os
import time

from semantic_atlas_demo_renderer.ideas import compose_prompt
from semantic_atlas_demo_renderer.schemas import Idea, RenderedImage

from .base import Renderer


class SDXLMpsRenderer(Renderer):
    name = "sdxl-mps"

    def __init__(self) -> None:
        try:
            import torch
            from diffusers import StableDiffusionXLPipeline
        except Exception as error:  # pragma: no cover - optional local-model path
            raise RuntimeError(
                "sdxl_mps requires the local-models dependency group: "
                "uv sync --group local-models"
            ) from error

        self._torch = torch
        model_id = os.environ.get("SDXL_MODEL_ID", "stabilityai/stable-diffusion-xl-base-1.0")
        dtype = torch.float16 if os.environ.get("DEVICE", "mps") == "mps" else torch.float32
        self.pipe = StableDiffusionXLPipeline.from_pretrained(
            model_id,
            torch_dtype=dtype,
            use_safetensors=True,
            local_files_only=os.environ.get("LOCAL_FILES_ONLY", "1") != "0",
        )
        self.pipe.to(os.environ.get("DEVICE", "mps"))

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
        start = time.perf_counter()
        prompt = compose_prompt(idea, x, y)
        generator = self._torch.Generator(device=os.environ.get("DEVICE", "mps")).manual_seed(world_seed)
        image = self.pipe(
            prompt=prompt,
            width=width,
            height=height,
            num_inference_steps=int(os.environ.get("SDXL_STEPS", "24")),
            guidance_scale=float(os.environ.get("SDXL_GUIDANCE", "5.0")),
            generator=generator,
        ).images[0]
        buffer = io.BytesIO()
        image.save(buffer, format="WEBP", quality=90)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return RenderedImage(
            imageUrl=f"data:image/webp;base64,{encoded}",
            width=width,
            height=height,
            x=x,
            y=y,
            seed=world_seed,
            elapsedMs=int((time.perf_counter() - start) * 1000),
            backend=self.name,
        )
