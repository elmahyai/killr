"""with_seed, local_seed, with_preserve_seed, local_preserve_seed (R's seed.R)."""

from __future__ import annotations

from . import _rng
from ._scope import current, force


def _restore(snap) -> None:
    if snap is None:
        _rng.remove_seed()
    else:
        _rng.restore(snap)


def with_preserve_seed(code):
    """Run code, then put back the generator state it started from."""
    old = _rng.snapshot()
    try:
        return force(code)
    finally:
        _restore(old)


def local_preserve_seed(*, _local_envir=None):
    old = _rng.snapshot()
    current(_local_envir).add(lambda: _restore(old))
    return old


def with_seed(seed, code, rng_kind=None, rng_normal_kind=None, rng_sample_kind=None):
    """Run code with set.seed(seed), then restore the previous state."""
    old = _rng.snapshot()
    try:
        _rng.set_seed(seed, rng_kind, rng_normal_kind, rng_sample_kind)
        return force(code)
    finally:
        _restore(old)


def local_seed(seed, *, _local_envir=None, rng_kind=None, rng_normal_kind=None,
               rng_sample_kind=None):
    old = _rng.snapshot()
    current(_local_envir).add(lambda: _restore(old))
    _rng.set_seed(seed, rng_kind, rng_normal_kind, rng_sample_kind)
    return seed
