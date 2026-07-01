from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Axis(BaseModel):
    negativeLabel: str
    positiveLabel: str
    negativePrompt: str
    positivePrompt: str


class Idea(BaseModel):
    id: str
    title: str
    family: str
    scene: str
    midpointPrompt: str
    xAxis: Axis
    yAxis: Axis
    palette: list[str] = Field(min_length=4, max_length=4)
    suffix: str


class PromptSetText(BaseModel):
    base: str
    x_negative: str
    x_positive: str
    y_negative: str
    y_positive: str
    x_negative_extreme: str | None = None
    x_positive_extreme: str | None = None
    y_negative_extreme: str | None = None
    y_positive_extreme: str | None = None


class GridRequest(BaseModel):
    ideaId: str
    gridSize: Literal[3] = 3
    worldSeed: int = Field(ge=0)
    width: int = Field(default=512, ge=256, le=1024)
    height: int = Field(default=512, ge=256, le=1024)


class CoordinateRequest(BaseModel):
    ideaId: str
    x: float = Field(ge=-1, le=1)
    y: float = Field(ge=-1, le=1)
    worldSeed: int = Field(ge=0)
    width: int = Field(default=512, ge=256, le=1024)
    height: int = Field(default=512, ge=256, le=1024)


class GridStartResponse(BaseModel):
    jobId: str
    backend: str


class RenderedImage(BaseModel):
    imageUrl: str
    width: int
    height: int
    x: float
    y: float
    seed: int
    elapsedMs: int
    backend: str
