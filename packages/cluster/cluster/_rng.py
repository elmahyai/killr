"""R's default Mersenne-Twister, so clusGap bootstrap draws match set.seed."""

from __future__ import annotations

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
