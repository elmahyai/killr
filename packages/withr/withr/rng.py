"""with_rng_version and local_rng_version (R's rng.R).

The kinds follow R's RNGversion(): R 1.6.x and earlier use Marsaglia-Multicarry,
R 2.x and R 3.0-3.5 use Mersenne-Twister with Rounding sampling, and R 3.6 on
use Rejection. R 0.x uses Wichmann-Hill, which is a named gap.
"""

from __future__ import annotations

from . import _rng
from ._gap import gap
from ._scope import current, force


def _set_version(version) -> None:
    parts = str(version).split(".")
    if len(parts) < 2:
        raise ValueError("malformed version string")
    major, minor = int(parts[0]), int(parts[1])
    if major == 0 and minor < 99:
        gap("with_rng_version", "R 0.x uses the Wichmann-Hill generator, which is not translated")
    if major == 0 or (major == 1 and minor <= 6):
        _rng.set_kind(_rng.MARSAGLIA, "Buggy Kinderman-Ramage", "Rounding")
    elif major <= 2 or (major == 3 and minor <= 5):
        _rng.set_kind(_rng.MERSENNE, "Inversion", "Rounding")
    else:
        _rng.set_kind(_rng.MERSENNE, "Inversion", "Rejection")


def _restore_kind(kind) -> None:
    _rng.set_kind(kind[0], kind[1], kind[2])


def with_rng_version(version, code):
    old = _rng.get_kind()
    try:
        _set_version(version)
        return force(code)
    finally:
        _restore_kind(old)


def local_rng_version(version, *, _local_envir=None):
    old = _rng.get_kind()
    current(_local_envir).add(lambda: _restore_kind(old))
    _set_version(version)
    return old
