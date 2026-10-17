"""Random draws from survreg-supported distributions (survival::rsurvreg).

R draws ``runif(n)`` from its default Mersenne-Twister stream and passes the
uniforms to ``qsurvreg``. ``RRandom`` reproduces R's ``set.seed`` scrambling
and its ``unif_rand`` fixup, so that ``set_seed(s)`` followed by ``rsurvreg``
gives the same numbers as ``set.seed(s)`` followed by ``rsurvreg`` in R.
"""

from __future__ import annotations

import os

import numpy as np

from survival.qsurvreg import qsurvreg

_MASK32 = 0xFFFFFFFF
_I2_32M1 = 2.328306437080797e-10  # 1 / (2^32 - 1)
_MT_N = 624


class RRandom:
    """R's default RNG: Mersenne-Twister with R's seed scrambling."""

    def __init__(self, seed=None):
        self._bit_generator = np.random.MT19937()
        if seed is None:
            seed = int.from_bytes(os.urandom(4), "little")
        self.set_seed(seed)

    def set_seed(self, seed):
        """Equivalent of R's ``set.seed(seed)``."""
        s = int(seed) & _MASK32
        for _ in range(50):
            s = (69069 * s + 1) & _MASK32
        state = np.empty(_MT_N, dtype=np.uint32)
        # The first of the 625 seed words is R's position counter; it is reset
        # to 624 below, which forces a full MT regeneration on the first draw.
        for j in range(_MT_N + 1):
            s = (69069 * s + 1) & _MASK32
            if j > 0:
                state[j - 1] = s
        self._bit_generator.state = {
            "bit_generator": "MT19937",
            "state": {"key": state, "pos": _MT_N},
        }

    def unif_rand(self, n):
        """Return ``n`` uniforms exactly as R's ``runif(n)`` does."""
        n = int(n)
        if n <= 0:
            return np.zeros(0, dtype=float)
        raw = self._bit_generator.random_raw(n).astype(np.float64)
        x = raw * 2.3283064365386963e-10
        x = np.where(x <= 0.0, 0.5 * _I2_32M1, x)
        x = np.where(1.0 - x <= 0.0, 1.0 - 0.5 * _I2_32M1, x)
        return x


_default_rng = RRandom()


def set_seed(seed):
    """Seed the default stream the way R's ``set.seed`` does."""
    _default_rng.set_seed(seed)


def rsurvreg(n, mean, scale=1, distribution="weibull", parms=None, rng=None):
    """Random survival times from a survreg distribution (survival::rsurvreg)."""
    if rng is None:
        rng = _default_rng
    u = rng.unif_rand(n)
    return qsurvreg(u, mean, scale, distribution=distribution, parms=parms)
