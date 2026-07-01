from __future__ import annotations

import base64
import io
import os
import time

from semantic_atlas_demo_renderer.ideas import compose_prompt
from semantic_atlas_demo_renderer.schemas import Idea, RenderedImage

from .base import Renderer


class Flux2KleinRenderer(Renderer):
    name = "flux2-klein-4b"

    def __init__(self) -> None:
        try:
            import torch
            from diffusers import Flux2KleinPipeline
        except Exception as error:  # pragma: no cover - optional CUDA path
            raise RuntimeError(
                "flux2_klein requires Diffusers with Flux2KleinPipeline and a CUDA-capable "
                "PyTorch install. Install the local-models dependency group and run on CUDA."
            ) from error

        self._torch = torch
        model_id = os.environ.get("FLUX2_MODEL_ID", "black-forest-labs/FLUX.2-klein-4B")
        dtype = torch.bfloat16 if os.environ.get("DEVICE", "cuda") == "cuda" else torch.float16
        self.pipe = Flux2KleinPipeline.from_pretrained(
            model_id,
            torch_dtype=dtype,
            local_files_only=os.environ.get("LOCAL_FILES_ONLY", "0") == "1",
        )
        self.pipe.to(os.environ.get("DEVICE", "cuda"))

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
        generator = self._torch.Generator(device=os.environ.get("DEVICE", "cuda")).manual_seed(world_seed)
        image = self.pipe(
            prompt=prompt,
            width=width,
            height=height,
            num_inference_steps=int(os.environ.get("FLUX2_STEPS", "4")),
            guidance_scale=float(os.environ.get("FLUX2_GUIDANCE", "1.0")),
            generator=generator,
            max_sequence_length=512,
            text_encoder_out_layers=(9, 18, 27),
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
