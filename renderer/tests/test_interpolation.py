from __future__ import annotations

from dataclasses import dataclass, field

from semantic_atlas_demo_renderer.interpolation import (
    EncodedPromptSet,
    InterpolationSettings,
    interpolate_conditioning,
)


@dataclass
class FakeTensor:
    value: float
    to_calls: list[dict[str, object]] = field(default_factory=list)

    def __sub__(self, other: object) -> FakeTensor:
        assert isinstance(other, FakeTensor)
        return FakeTensor(self.value - other.value)

    def __add__(self, other: object) -> FakeTensor:
        assert isinstance(other, FakeTensor)
        return FakeTensor(self.value + other.value)

    def __mul__(self, other: float) -> FakeTensor:
        return FakeTensor(self.value * float(other))

    def to(self, **kwargs: object) -> FakeTensor:
        self.to_calls.append(kwargs)
        return self


def test_interpolate_conditioning_composes_x_and_y_endpoint_deltas() -> None:
    encoded = EncodedPromptSet(
        base=FakeTensor(10.0),
        x_negative=FakeTensor(1.0),
        x_positive=FakeTensor(14.0),
        y_negative=FakeTensor(3.0),
        y_positive=FakeTensor(20.0),
    )

    result = interpolate_conditioning(
        encoded,
        x=1.0,
        y=-1.0,
        settings=InterpolationSettings(edge_boost=0.0),
    )

    assert isinstance(result, FakeTensor)
    assert result.value == 7.0


def test_interpolate_conditioning_keeps_center_on_base() -> None:
    encoded = EncodedPromptSet(
        base=FakeTensor(10.0),
        x_negative=FakeTensor(1.0),
        x_positive=FakeTensor(14.0),
        y_negative=FakeTensor(3.0),
        y_positive=FakeTensor(20.0),
    )

    result = interpolate_conditioning(
        encoded,
        x=0.0,
        y=0.0,
        settings=InterpolationSettings(edge_boost=0.0),
    )

    assert isinstance(result, FakeTensor)
    assert result.value == 10.0
