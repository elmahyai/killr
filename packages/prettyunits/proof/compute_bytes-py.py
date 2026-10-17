"""Proof: prettyunits.bytes.compute_bytes against the R prettyunits 1.2.0 result."""

from harness import run_proof

from prettyunits.bytes import compute_bytes

NAN = float("nan")
INF = float("inf")
X = [None, NAN, -1.0, 0.0, 1.0, 999.0, 1000.0, 1e4, 999949.0, 999950.0, 1e6, -1e5,
     1.5e9, 2.5e12, 1e18, 1e24, INF, -INF]


def one():
    a = compute_bytes(X)
    b = compute_bytes(X, smallest_unit="kB")
    return {
        "default": {"amount": a.amount, "unit": a.unit, "negative": a.negative},
        "kB": {"amount": b.amount, "unit": b.unit, "negative": b.negative},
    }


run_proof("compute_bytes", one)
