"""R's default uniform stream for the permute shuffle functions.

Mersenne-Twister seeded the way R seeds it (RNG.c), with R's ``unif_rand``
and ``R_unif_index`` (Rejection sampling, R >= 3.6). ``set_seed`` matches
R's ``set.seed(seed)`` under the default ``RNGkind``. ``sample_int`` matches
R's ``sample.int(n, size, replace = FALSE)``, including the hash path that
R takes for ``n > 1e7`` (``sample2``).

The generator is copied from ``packages/boot/boot/rng.py``, which is checked
against R; the copy stays in this package like the other ``_rng.py`` modules.
"""

from __future__ import annotations

import math
import os
import time

_N = 624
_M = 397
_MATRIX_A = 0x9908B0DF
_UPPER = 0x80000000
_LOWER = 0x7FFFFFFF
_I2_32 = 2.3283064365386963e-10
_I2_32M1 = 2.328306437080797e-10
_MASK = 0xFFFFFFFF

_mt = [0] * _N
_mti = _N + 1
_seeded = False


def set_seed(seed: int) -> None:
    """Match R's ``set.seed(seed)`` under the default RNG kind."""
    global _mti, _seeded
    seed &= _MASK
    for _ in range(50):
        seed = (69069 * seed + 1) & _MASK
    dummy = []
    for _ in range(1 + _N):
        seed = (69069 * seed + 1) & _MASK
        dummy.append(seed)
    dummy[0] = _N  # FixupSeeds: mti = N
    for i in range(_N):
        _mt[i] = dummy[i + 1]
    _mti = dummy[0]
    _seeded = True


def _ensure_seeded() -> None:
    if not _seeded:
        set_seed((int(time.time() * 1e6) ^ (os.getpid() << 16)) & _MASK)


def unif_rand() -> float:
    """One draw from R's ``unif_rand`` (Mersenne-Twister), in (0, 1)."""
    global _mti
    _ensure_seeded()
    mag01 = (0, _MATRIX_A)
    if _mti >= _N:
        for kk in range(_N - _M):
            y = (_mt[kk] & _UPPER) | (_mt[kk + 1] & _LOWER)
            _mt[kk] = (_mt[kk + _M] ^ (y >> 1) ^ mag01[y & 1]) & _MASK
        for kk in range(_N - _M, _N - 1):
            y = (_mt[kk] & _UPPER) | (_mt[kk + 1] & _LOWER)
            _mt[kk] = (_mt[kk + (_M - _N)] ^ (y >> 1) ^ mag01[y & 1]) & _MASK
        y = (_mt[_N - 1] & _UPPER) | (_mt[0] & _LOWER)
        _mt[_N - 1] = (_mt[_M - 1] ^ (y >> 1) ^ mag01[y & 1]) & _MASK
        _mti = 0
    y = _mt[_mti] & _MASK
    _mti += 1
    y ^= y >> 11
    y ^= (y << 7) & 0x9D2C5680
    y ^= (y << 15) & 0xEFC60000
    y ^= y >> 18
    y &= _MASK
    x = y * _I2_32
    if x <= 0.0:
        return 0.5 * _I2_32M1
    if (1.0 - x) <= 0.0:
        return 1.0 - 0.5 * _I2_32M1
    return x


def _rbits(bits: int) -> int:
    v = 0
    for _ in range(0, bits + 1, 16):
        v = 65536 * v + math.floor(unif_rand() * 65536)
    return v & ((1 << bits) - 1)


def unif_index(dn: float) -> int:
    """R_unif_index for sample.kind 'Rejection'. Result is in 0 .. dn-1."""
    if dn <= 0:
        return 0
    bits = int(math.ceil(math.log2(dn)))
    while True:
        dv = _rbits(bits)
        if dn > dv:
            return dv


def sample_int(n: float, size: int, replace: bool = False):
    """R's sample.int(n, size, replace = FALSE) without prob. Values are 1-based."""
    size = int(size)
    if replace or size < 2:
        if not replace and size > n:
            raise ValueError("cannot take a sample larger than the population when 'replace = FALSE'")
        return [unif_index(n) + 1 for _ in range(size)]
    if size > n:
        raise ValueError("cannot take a sample larger than the population when 'replace = FALSE'")
    if n > 1e7 and size <= n / 2:
        # R's sample2: draw until the value is new.
        seen = set()
        out = []
        while len(out) < size:
            v = unif_index(n)
            if v not in seen:
                seen.add(v)
                out.append(v + 1)
        return out
    if n != int(n):
        raise ValueError("non-integer population size is not supported")
    pool = list(range(int(n)))
    out = []
    m = int(n)
    for _ in range(size):
        j = unif_index(m)
        out.append(pool[j] + 1)
        pool[j] = pool[m - 1]
        m -= 1
    return out
