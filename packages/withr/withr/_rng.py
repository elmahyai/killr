"""R's uniform random streams, seeded the way R seeds them (RNG.c).

Mersenne-Twister (R's default) and Marsaglia-Multicarry are translated. The
50-step seed scrambling, the seed-to-state map, the Marsaglia step, and the
uniform fix-up follow R. ``runif`` and ``set_seed`` are the stand-ins for R's
base ``runif`` and ``set.seed``; the proofs call them directly. Other uniform
kinds are a named gap.
"""

from __future__ import annotations

import os
import random
import time

from ._gap import gap

MERSENNE = "Mersenne-Twister"
MARSAGLIA = "Marsaglia-Multicarry"
_KINDS = (MERSENNE, MARSAGLIA)
_NORMAL_KINDS = (
    "Inversion",
    "Buggy Kinderman-Ramage",
    "Ahrens-Dieter",
    "Box-Muller",
    "Kinderman-Ramage",
    "user-supplied",
)
_SAMPLE_KINDS = ("Rounding", "Rejection")
_MASK = 0xFFFFFFFF
_MT_SCALE = 2.3283064365386963e-10  # 2^-32, Mersenne-Twister genrand scale
_MM_SCALE = 2.328306437080797e-10  # 1 / (2^32 - 1), Marsaglia-Multicarry scale
_UINT_MAX = 4294967295.0


class _State:
    kind = MERSENNE
    normal = "Inversion"
    sample = "Rejection"
    # random.Random for Mersenne-Twister, [I1, I2] for Marsaglia, None if unseeded.
    engine = None


_S = _State()


def _next(seed: int) -> int:
    return (69069 * seed + 1) & _MASK


def _init(kind: str, seed: int):
    """RNG_Init: 50 scrambling steps, then fill the state words."""
    seed &= _MASK
    for _ in range(50):
        seed = _next(seed)
    if kind == MERSENNE:
        words = []
        for _ in range(625):
            seed = _next(seed)
            words.append(seed)
        engine = random.Random()
        # words[0] is R's position word; FixupSeeds sets it to 624 (mti = N).
        engine.setstate((3, tuple(words[1:]) + (624,), None))
        return engine
    seed = _next(seed)
    i1 = seed
    seed = _next(seed)
    i2 = seed
    return [i1 or 1, i2 or 1]


def _time_seed() -> int:
    return (int(time.time() * 1e6) ^ (os.getpid() << 16)) & _MASK


def _ensure_seeded() -> None:
    if _S.engine is None:
        _S.engine = _init(_S.kind, _time_seed())


def _fixup(x: float) -> float:
    half = 0.5 * _MM_SCALE
    if x <= 0.0:
        return half
    if 1.0 - x <= 0.0:
        return 1.0 - half
    return x


def _unif_rand() -> float:
    _ensure_seeded()
    if _S.kind == MERSENNE:
        return _fixup(_S.engine.getrandbits(32) * _MT_SCALE)
    i1, i2 = _S.engine
    i1 = (36969 * (i1 & 0xFFFF) + (i1 >> 16)) & _MASK
    i2 = (18000 * (i2 & 0xFFFF) + (i2 >> 16)) & _MASK
    _S.engine = [i1, i2]
    return _fixup((((i1 << 16) & _MASK) ^ (i2 & 0xFFFF)) * _MM_SCALE)


def get_kind() -> tuple[str, str, str]:
    """RNGkind(): the uniform, normal and sample kinds."""
    _ensure_seeded()
    return (_S.kind, _S.normal, _S.sample)


def set_kind(kind=None, normal=None, sample=None) -> tuple[str, str, str]:
    """RNGkind(kind, normal.kind, sample.kind). A new uniform kind is seeded from
    the old stream, as R does. Returns the previous kinds."""
    old = get_kind()
    if kind is not None:
        if kind not in _KINDS:
            gap(
                "RNGkind",
                f"uniform kind {kind!r} is not translated; only "
                "Mersenne-Twister and Marsaglia-Multicarry are",
            )
        u = _unif_rand()
        _S.kind = kind
        _S.engine = _init(kind, int(u * _UINT_MAX))
    if normal is not None:
        if normal not in _NORMAL_KINDS:
            raise ValueError(f"unknown normal kind {normal!r}")
        _S.normal = normal
    if sample is not None:
        if sample not in _SAMPLE_KINDS:
            raise ValueError(f"unknown sample kind {sample!r}")
        _S.sample = sample
    return old


def set_seed(seed, kind=None, normal=None, sample=None) -> None:
    """set.seed(seed), after RNGkind(kind, normal, sample) when any is given."""
    if kind is not None or normal is not None or sample is not None:
        set_kind(kind, normal, sample)
    _S.engine = _init(_S.kind, int(seed))


def remove_seed() -> None:
    """rm(.Random.seed): the next draw seeds from the clock again."""
    _S.engine = None


def snapshot():
    """The whole generator state, or None when unseeded (no .Random.seed)."""
    if _S.engine is None:
        return None
    state = _S.engine.getstate() if _S.kind == MERSENNE else list(_S.engine)
    return (_S.kind, _S.normal, _S.sample, state)


def restore(snap) -> None:
    if snap is None:
        _S.engine = None
        return
    kind, normal, sample, state = snap
    _S.kind, _S.normal, _S.sample = kind, normal, sample
    if kind == MERSENNE:
        engine = random.Random()
        engine.setstate(state)
        _S.engine = engine
    else:
        _S.engine = list(state)


def runif(n: int) -> list[float]:
    """runif(n) for the current kind."""
    return [_unif_rand() for _ in range(int(n))]
