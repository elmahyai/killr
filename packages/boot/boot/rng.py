"""R 4.5 Mersenne-Twister and rejection sampling, matching set.seed.

Do not replace this with NumPy's generator. Bootstrap replicates are checked
against R, so sample.int has to draw the same integers.
"""

from __future__ import annotations

import math

_N = 624
_M = 397
_MATRIX_A = 0x9908B0DF
_UPPER = 0x80000000
_LOWER = 0x7FFFFFFF
_I2_32 = 2.3283064365386963e-10
_I2_32M1 = 2.328306437080797e-10

_mt = [0] * _N
_mti = _N + 1


def set_seed(seed: int) -> None:
    """Match R set.seed(seed) under the default RNGkind."""
    global _mti
    seed &= 0xFFFFFFFF
    for _ in range(50):
        seed = (69069 * seed + 1) & 0xFFFFFFFF
    dummy = []
    for _ in range(1 + _N):
        seed = (69069 * seed + 1) & 0xFFFFFFFF
        dummy.append(seed)
    dummy[0] = _N
    for i in range(_N):
        _mt[i] = dummy[i + 1]
    _mti = dummy[0]


def unif() -> float:
    """One draw from R's unif_rand, in (0, 1)."""
    global _mti
    mag01 = (0, _MATRIX_A)
    if _mti >= _N:
        for kk in range(_N - _M):
            y = (_mt[kk] & _UPPER) | (_mt[kk + 1] & _LOWER)
            _mt[kk] = (_mt[kk + _M] ^ (y >> 1) ^ mag01[y & 1]) & 0xFFFFFFFF
        for kk in range(_N - _M, _N - 1):
            y = (_mt[kk] & _UPPER) | (_mt[kk + 1] & _LOWER)
            _mt[kk] = (_mt[kk + (_M - _N)] ^ (y >> 1) ^ mag01[y & 1]) & 0xFFFFFFFF
        y = (_mt[_N - 1] & _UPPER) | (_mt[0] & _LOWER)
        _mt[_N - 1] = (_mt[_M - 1] ^ (y >> 1) ^ mag01[y & 1]) & 0xFFFFFFFF
        _mti = 0
    y = _mt[_mti] & 0xFFFFFFFF
    _mti += 1
    y ^= y >> 11
    y ^= (y << 7) & 0x9D2C5680
    y ^= (y << 15) & 0xEFC60000
    y ^= y >> 18
    y &= 0xFFFFFFFF
    x = y * _I2_32
    if x <= 0.0:
        return 0.5 * _I2_32M1
    if (1.0 - x) <= 0.0:
        return 1.0 - 0.5 * _I2_32M1
    return x


def unif_index(dn: int) -> int:
    """R_unif_index for sample.kind 'Rejection'. Result is in 0 .. dn-1."""
    if dn <= 0:
        return 0
    bits = math.ceil(math.log2(dn))
    mask = (1 << bits) - 1
    while True:
        value = 0
        for _ in range(0, bits + 1, 16):
            value = 65536 * value + math.floor(unif() * 65536)
        draw = value & mask
        if dn > draw:
            return draw


def sample_int(n: int, size: int | None = None, replace: bool = False) -> list[int]:
    """R sample.int(n, size, replace). Values are 1-based, as in R."""
    if size is None:
        size = n
    if not replace and size > n:
        raise ValueError("cannot take a sample larger than the population when replace is false")
    if replace or size < 2:
        return [unif_index(n) + 1 for _ in range(size)]
    pool = list(range(n))
    out = []
    remaining = n
    for _ in range(size):
        j = unif_index(remaining)
        out.append(pool[j] + 1)
        remaining -= 1
        pool[j] = pool[remaining]
    return out
