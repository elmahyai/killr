"""Proof: prettyunits.numbers.compute_num against the R prettyunits 1.2.0 result."""

from harness import run_proof

from prettyunits.numbers import compute_num

NAN = float("nan")
INF = float("inf")
Y = [None, NAN, -1.0, 0.0, 1e-25, 1.3333e-5, 999.0, 1000.0, 999950.0, 1e6, -2.5e9,
     1e30, 1e-30, INF, -INF, 0.5, 1e-300, -1e-17]


def one():
    a = compute_num(Y)
    b = compute_num(Y, smallest_prefix="m")
    return {
        "default": {"amount": a.amount, "prefix": a.prefix, "negative": a.negative},
        "m": {"amount": b.amount, "prefix": b.prefix, "negative": b.negative},
    }


run_proof("compute_num", one)
