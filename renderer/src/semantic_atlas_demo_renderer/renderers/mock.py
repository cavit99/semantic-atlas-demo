from __future__ import annotations

import base64
import hashlib
import io
import math
import random
import time

from PIL import Image, ImageDraw, ImageFilter

from semantic_atlas_demo_renderer.schemas import Idea, RenderedImage

from .base import Renderer


class MockRenderer(Renderer):
    name = "mock-live"

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
        seed = coordinate_seed(idea.id, world_seed, x, y)
        rng = random.Random(seed)
        colors = [hex_to_rgb(color) for color in idea.palette]

        image = Image.new("RGB", (width, height), colors[3])
        draw = ImageDraw.Draw(image, "RGBA")

        draw_gradient(draw, width, height, colors, x, y)
        draw_field_lines(draw, width, height, colors, x, y)
        draw_scene_marks(draw, width, height, colors, x, y, rng)
        image = image.filter(ImageFilter.UnsharpMask(radius=1.2, percent=125))

        buffer = io.BytesIO()
        image.save(buffer, format="WEBP", quality=88)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return RenderedImage(
            imageUrl=f"data:image/webp;base64,{encoded}",
            width=width,
            height=height,
            x=x,
            y=y,
            seed=seed,
            elapsedMs=elapsed_ms,
            backend=self.name,
        )


def coordinate_seed(idea_id: str, world_seed: int, x: float, y: float) -> int:
    key = f"{idea_id}:{world_seed}:{x:.3f}:{y:.3f}".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:4], "big")


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def rgba(color: tuple[int, int, int], alpha: int) -> tuple[int, int, int, int]:
    return color[0], color[1], color[2], alpha


def draw_gradient(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    colors: list[tuple[int, int, int]],
    x: float,
    y: float,
) -> None:
    for row in range(height):
        t = row / max(1, height - 1)
        warm = (x + 1) / 2
        cool = (y + 1) / 2
        r = int(colors[3][0] * (1 - t) + colors[0][0] * t * (0.55 + warm * 0.45))
        g = int(colors[3][1] * (1 - t) + colors[1][1] * t * (0.55 + cool * 0.45))
        b = int(colors[3][2] * (1 - t) + colors[2][2] * t)
        draw.line((0, row, width, row), fill=(r, g, b, 255))


def draw_field_lines(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    colors: list[tuple[int, int, int]],
    x: float,
    y: float,
) -> None:
    center_x = width * (0.5 + x * 0.08)
    center_y = height * (0.5 - y * 0.08)
    for index in range(18):
        angle = index * math.tau / 18 + x * 0.35
        radius = width * (0.16 + index * 0.025)
        left = center_x + math.cos(angle) * radius
        top = center_y + math.sin(angle) * radius * (0.74 + y * 0.16)
        right = center_x + math.cos(angle + 1.8 + y * 0.2) * radius * 1.36
        bottom = center_y + math.sin(angle + 1.8) * radius
        draw.line((left, top, right, bottom), fill=rgba(colors[index % 3], 70), width=2 + index % 4)


def draw_scene_marks(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    colors: list[tuple[int, int, int]],
    x: float,
    y: float,
    rng: random.Random,
) -> None:
    density = int(18 + (x + 1) * 18)
    height_bias = 0.8 + (y + 1) * 0.35
    for index in range(density):
        size = rng.randint(width // 32, width // 9)
        cx = rng.randint(size, width - size)
        cy = rng.randint(size, height - size)
        stretch = 0.55 + rng.random() * height_bias
        color = colors[(index + int(abs(y) * 3)) % len(colors)]
        alpha = rng.randint(70, 150)
        shape = rng.choice(["ellipse", "rect", "arc"])
        box = (
            cx - size,
            cy - int(size * stretch),
            cx + size,
            cy + int(size * stretch),
        )
        if shape == "ellipse":
            draw.ellipse(box, outline=rgba(color, alpha), width=rng.randint(2, 5))
        elif shape == "rect":
            draw.rounded_rectangle(box, radius=max(3, size // 5), outline=rgba(color, alpha), width=2)
        else:
            draw.arc(box, start=rng.randint(0, 180), end=rng.randint(190, 350), fill=rgba(color, alpha), width=3)
