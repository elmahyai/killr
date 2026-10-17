"""Window bounds for slide() and hop().

The iteration matches slider's C loop: a window is inclusive on both
ends, partial windows are clipped, and a window that misses `.x`
entirely is empty. Positions the step skips stay missing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from slider.errors import SliderError


@dataclass(frozen=True)
class IterOpts:
    iter_min: int
    iter_max: int
    iter_step: int
    start: int
    start_step: int
    stop: int
    stop_step: int
    size: int


def _missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def _as_int(value, name: str, *, dot: bool) -> tuple[int, bool]:
    """Return the integer and whether it is unbounded (Inf)."""
    label = f".{name}" if dot else name
    if _missing(value):
        raise SliderError(f"`{label}` can't be missing.")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SliderError(f"`{label}` must be a number.")
    if isinstance(value, float) and math.isinf(value):
        if value < 0:
            raise SliderError(f"`{label}` can't be negative infinity.")
        return 0, True
    if isinstance(value, float) and not value.is_integer():
        raise SliderError(f"`{label}` must be a whole number, not {value}.")
    return int(value), False


def _check_signs(before: int, after: int, before_unbounded: bool, after_unbounded: bool, before_positive: bool, after_positive: bool) -> None:
    if not before_positive and not after_positive and not before_unbounded and not after_unbounded:
        raise SliderError(
            f"`.before` ({before}) and `.after` ({after}) can't both be negative."
        )
    if not after_positive and not before_unbounded and abs(after) > before:
        raise SliderError(
            "When `.after` ({after}) is negative, its absolute value ({abs_after}) "
            "can't be greater than `.before` ({before}).".format(
                after=after, abs_after=abs(after), before=before
            )
        )
    if not before_positive and not after_unbounded and abs(before) > after:
        raise SliderError(
            "When `.before` ({before}) is negative, its absolute value ({abs_before}) "
            "can't be greater than `.after` ({after}).".format(
                before=before, abs_before=abs(before), after=after
            )
        )


def validate_step(step, *, dot: bool) -> int:
    label = ".step" if dot else "step"
    if _missing(step):
        raise SliderError(f"`{label}` can't be missing.")
    if isinstance(step, bool) or not isinstance(step, (int, float)):
        raise SliderError(f"`{label}` must be a number.")
    if isinstance(step, float) and not step.is_integer():
        raise SliderError(f"`{label}` must be a whole number, not {step}.")
    step = int(step)
    if step < 1:
        raise SliderError(f"`{label}` must be at least 1, not {step}.")
    return step


def validate_bool(value, name: str, *, dot: bool) -> bool:
    label = f".{name}" if dot else name
    if _missing(value):
        raise SliderError(f"`{label}` can't be missing.")
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    raise SliderError(f"`{label}` must be TRUE or FALSE.")


def iter_opts(before, after, step, complete, size: int, *, dot: bool) -> IterOpts:
    before, before_unbounded = _as_int(before, "before", dot=dot)
    after, after_unbounded = _as_int(after, "after", dot=dot)
    before_positive = before >= 0
    after_positive = after >= 0
    _check_signs(before, after, before_unbounded, after_unbounded, before_positive, after_positive)
    step = validate_step(step, dot=dot)
    complete = validate_bool(complete, "complete", dot=dot)

    iter_min = 0
    iter_max = size
    if complete:
        if before_positive and not before_unbounded:
            iter_min += before
        if after_positive and not after_unbounded:
            iter_max -= after

    offset = before if complete and before_positive and not before_unbounded else 0
    if before_unbounded:
        start = 0
        start_step = 0
    else:
        start = offset - before
        start_step = step
    if after_unbounded:
        stop = size - 1
        stop_step = 0
    else:
        stop = offset + after
        stop_step = step
    return IterOpts(iter_min, iter_max, step, start, start_step, stop, stop_step, size)


def windows(opts: IterOpts):
    """Yield (output index, inclusive start, inclusive stop) in 0-based positions.

    An empty window is yielded as (index, None, None).
    """
    start = opts.start
    stop = opts.stop
    size = opts.size
    index = opts.iter_min
    while index < opts.iter_max:
        window_start = max(start, 0)
        window_stop = min(stop, size - 1)
        if window_stop < window_start:
            yield index, None, None
        else:
            yield index, window_start, window_stop
        start += opts.start_step
        stop += opts.stop_step
        index += opts.iter_step


def slice_at(values: list, start, stop) -> list:
    if start is None:
        return []
    return values[start : stop + 1]
