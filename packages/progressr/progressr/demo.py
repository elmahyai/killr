"""Demo sums and square roots that signal progression conditions."""

from __future__ import annotations

import math
import time

from progressr.condition import message as r_message
from progressr.condition import r_warning
from progressr.options import ProgressrError, get_option
from progressr.progressor import progressor


_MISSING = object()


def _fmt_g(value) -> str:
    """R sprintf %g for the values these demos print."""
    number = float(value)
    if math.isnan(number):
        return "NaN"
    if math.isinf(number):
        return "Inf" if number > 0 else "-Inf"
    return format(number, "g")


def _vector(x):
    if isinstance(x, (str, bytes)):
        raise ProgressrError("x must be a numeric vector")
    if isinstance(x, range):
        return list(x), True
    dtype = getattr(x, "dtype", None)
    if dtype is not None and getattr(dtype, "kind", None) in {"i", "u"}:
        return [int(item) for item in x], True
    if isinstance(x, (list, tuple)):
        return list(x), all(type(item) is int for item in x)
    return [item for item in x], False


def _flag(value, demo_name, hidden_name, fallback):
    """An omitted argument reads the demo option, then the hidden option."""
    if value is _MISSING:
        current = get_option(demo_name, fallback)
        return get_option(hidden_name, current)
    return value


def _delay(value, fallback):
    if value is _MISSING:
        return get_option("progressr.demo.delay", fallback)
    return value


def _pause(delay) -> None:
    time.sleep(0.2 * delay)


def _sqrt_value(value):
    number = float(value)
    if math.isnan(number):
        return number
    if number < 0:
        r_warning("NaNs produced")
        return math.nan
    return math.sqrt(number)


def _walk(x, delay, stdout, message_flag, sticky, progress, progress_text, value_text, consume):
    values, _integer = _vector(x)
    if progress:
        reporter = progressor(along=values)
    else:
        def reporter(*_args, **_kwargs):
            return None

    for index, value in enumerate(values):
        kk = index + 1
        reporter(amount=0)
        _pause(delay)
        if stdout:
            print(f"O: Element #{kk}", flush=True)
        _pause(delay)
        reporter(amount=0)
        _pause(delay)
        consumed = consume(value)
        reporter(message=progress_text(kk))
        _pause(delay)
        if message_flag:
            r_message(value_text(consumed))
        reporter(amount=0)
        _pause(delay)
        if sticky and kk % 10 == 0:
            reporter(amount=0, message=f"P: {kk} elements done", class_="sticky")
    reporter(amount=0)
    return values


def slow_sum_p(
    x,
    delay=_MISSING,
    stdout=_MISSING,
    message=_MISSING,
    sticky=_MISSING,
    progress=_MISSING,
):
    """Sum x, sleeping and optionally signaling after each element."""
    delay = _delay(delay, 1.0)
    stdout = _flag(stdout, "progressr.demo.stdout", "progressr.slow_sum_p.stdout", False)
    message = _flag(message, "progressr.demo.message", "progressr.slow_sum_p.message", True)
    sticky = _flag(sticky, "progressr.demo.sticky", "progressr.slow_sum_p.sticky", True)
    progress = _flag(progress, "progressr.demo.progress", "progressr.slow_sum_p.progress", True)
    values, integer = _vector(x)
    total = 0 if integer else 0.0

    def consume(value):
        nonlocal total
        total = total + (int(value) if integer else float(value))
        return value

    _walk(
        values,
        delay,
        stdout,
        message,
        sticky,
        progress,
        lambda kk: f"P: Adding {_fmt_g(kk)}",
        lambda value: f"M: Added value {_fmt_g(value)}",
        consume,
    )
    return total


def slow_sum(x, delay=_MISSING, stdout=False, message=False, sticky=False, progress=False):
    """Sum x with the demo signals off unless the caller turns one on."""
    if delay is _MISSING:
        delay = get_option("progressr.demo.delay", 1.0)
    return slow_sum_p(
        x,
        delay=delay,
        stdout=stdout,
        message=message,
        sticky=sticky,
        progress=progress,
    )


def slow_sqrt_p(
    x,
    delay=_MISSING,
    stdout=_MISSING,
    message=_MISSING,
    sticky=_MISSING,
    progress=_MISSING,
):
    """Square root of each element, sleeping and optionally signaling."""
    delay = _delay(delay, 0.5)
    stdout = _flag(stdout, "progressr.demo.stdout", "progressr.slow_sqrt_p.stdout", False)
    message = _flag(message, "progressr.demo.message", "progressr.slow_sqrt_p.message", True)
    sticky = _flag(sticky, "progressr.demo.sticky", "progressr.slow_sqrt_p.sticky", True)
    progress = _flag(progress, "progressr.demo.progress", "progressr.slow_sqrt_p.progress", True)
    result = []

    def consume(value):
        calculated = _sqrt_value(value)
        result.append(calculated)
        return calculated

    _walk(
        x,
        delay,
        stdout,
        message,
        sticky,
        progress,
        lambda kk: f"P: Calculating sqrt({_fmt_g(kk)})",
        lambda value: f"M: Calculated value {_fmt_g(value)}",
        consume,
    )
    return result


def slow_sqrt(x, delay=_MISSING, stdout=False, message=False, sticky=False, progress=False):
    """Square roots with the demo signals off unless the caller turns one on."""
    if delay is _MISSING:
        delay = get_option("progressr.demo.delay", 0.5)
    return slow_sqrt_p(
        x,
        delay=delay,
        stdout=stdout,
        message=message,
        sticky=sticky,
        progress=progress,
    )
