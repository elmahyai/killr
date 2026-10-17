"""Proof: prettyunits.ago.vague_dt against the R prettyunits 1.2.0 result."""

from harness import run_proof, try_val

from prettyunits._difftime import Difftime
from prettyunits.ago import vague_dt

NAN = float("nan")
SECS = [-30.0, 0.0, 5.0, 9.9, 10.0, 30.0, 44.9, 50.0, 60.0, 89.0, 90.0, 600.0,
        2699.0, 2700.0, 3599.0, 5400.0, 7200.0, 42 * 3600.0 - 1, 42 * 3600.0,
        86400.0, 24 * 3600.0, 30 * 86400.0, 45 * 86400.0, 335 * 86400.0,
        365 * 86400.0, 1.5 * 365.25 * 86400, 3650 * 86400.0, None, NAN]


def one():
    out = {}
    for fmt in ("default", "short", "terse"):
        out[fmt] = [try_val(vague_dt, Difftime(s, units="secs"), format=fmt) for s in SECS]
    out["empty"] = vague_dt(Difftime([], units="secs"))
    return out


run_proof("vague_dt", one)
