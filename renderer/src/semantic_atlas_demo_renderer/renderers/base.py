from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from semantic_atlas_demo_renderer.schemas import Idea, RenderedImage


class Renderer(ABC):
    name: str
    grid_batch_size: int = 1

    @abstractmethod
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
        """Render one coordinate."""

    async def render_many(
        self,
        *,
        idea: Idea,
        points: list[dict[str, Any]],
        world_seed: int,
        width: int,
        height: int,
    ) -> list[RenderedImage]:
        return [
            await self.render(
                idea=idea,
                x=float(point["x"]),
                y=float(point["y"]),
                world_seed=world_seed,
                width=width,
                height=height,
            )
            for point in points
        ]
