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
    step_scale: float = 1.0
    x_gain: float = 1.0
    y_gain: float = 1.0
    edge_start: float = 0.55
    edge_boost: float = 0.75


@dataclass(frozen=True)
class EncodedPromptSet:
    base: TensorT
    x_negative: TensorT
    x_positive: TensorT
    y_negative: TensorT
    y_positive: TensorT
    x_negative_extreme: TensorT | None = None
    x_positive_extreme: TensorT | None = None
    y_negative_extreme: TensorT | None = None
    y_positive_extreme: TensorT | None = None


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, float(value)))
    return value * value * (3.0 - 2.0 * value)


def blend_axis(
    base: TensorT,
    negative: TensorT,
    positive: TensorT,
    negative_extreme: TensorT | None,
    positive_extreme: TensorT | None,
    coord: float,
    *,
    step_scale: float,
    gain: float,
    edge_start: float,
    edge_boost: float,
) -> TensorT:
    signed = float(coord)
    if abs(signed) < 1e-6:
        return base

    magnitude = abs(signed) * float(step_scale) * float(gain)
    pole = positive if signed >= 0.0 else negative
    extreme = positive_extreme if signed >= 0.0 else negative_extreme

    edge_start = max(1e-4, min(0.95, float(edge_start)))
    reached = min(magnitude, 1.0)

    if reached <= edge_start:
        t = smoothstep(reached / edge_start)
        return base + (pole - base) * t

    edge_t = smoothstep((reached - edge_start) / max(1e-4, 1.0 - edge_start))
    if extreme is not None:
        return pole + (extreme - pole) * edge_t

    overshoot = 1.0 + float(edge_boost) * edge_t
    return base + (pole - base) * overshoot


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
        prompts.x_negative_extreme,
        prompts.x_positive_extreme,
        x,
        step_scale=settings.step_scale,
        gain=settings.x_gain,
        edge_start=settings.edge_start,
        edge_boost=settings.edge_boost,
    )
    y_tensor = blend_axis(
        prompts.base,
        prompts.y_negative,
        prompts.y_positive,
        prompts.y_negative_extreme,
        prompts.y_positive_extreme,
        y,
        step_scale=settings.step_scale,
        gain=settings.y_gain,
        edge_start=settings.edge_start,
        edge_boost=settings.edge_boost,
    )
    return prompts.base + (x_tensor - prompts.base) + (y_tensor - prompts.base)
