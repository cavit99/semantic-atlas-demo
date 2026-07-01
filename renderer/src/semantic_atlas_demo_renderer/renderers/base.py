from __future__ import annotations

from abc import ABC, abstractmethod

from semantic_atlas_demo_renderer.schemas import Idea, RenderedImage


class Renderer(ABC):
    name: str

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
