from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar


class TensorLike(Protocol):
    def __sub__(self, other: object) -> TensorLike: ...
    def __add__(self, other: object) -> TensorLike: ...
    def __mul__(self, other: float) -> TensorLike: ...


TensorT = TypeVar("TensorT", bound=TensorLike)


@dataclass(frozen=True)
class InterpolationSettings:
    pass


@dataclass(frozen=True)
class EncodedPromptSet:
    base: TensorT
    x_negative: TensorT
    x_positive: TensorT
    y_negative: TensorT
    y_positive: TensorT


def blend_axis(
    base: TensorT,
    negative: TensorT,
    positive: TensorT,
    coord: float,
) -> TensorT:
    signed = float(coord)
    if abs(signed) < 1e-6:
        return base

    magnitude = max(0.0, min(1.0, abs(signed)))
    pole = positive if signed >= 0.0 else negative
    return base + (pole - base) * magnitude


def interpolate_conditioning(
    prompts: EncodedPromptSet,
    *,
    x: float,
    y: float,
    settings: InterpolationSettings,
) -> TensorLike:
    x_tensor = blend_axis(
        prompts.base,
        prompts.x_negative,
        prompts.x_positive,
        x,
    )
    y_tensor = blend_axis(
        prompts.base,
        prompts.y_negative,
        prompts.y_positive,
        y,
    )
    return prompts.base + (x_tensor - prompts.base) + (y_tensor - prompts.base)
