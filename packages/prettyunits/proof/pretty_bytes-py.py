"""Proof: prettyunits.bytes.pretty_bytes against the R prettyunits 1.2.0 result."""

from harness import run_proof, try_val

from prettyunits.bytes import pretty_bytes

NAN = float("nan")
INF = float("inf")
X = [None, NAN, -1.0, 0.0, 1.0, 999.0, 1000.0, 1e4, 999949.0, 999950.0, 1e6, -1e5,
     1.5e9, 2.5e12, 1e18, 1e24]


def one():
    return {
        "default": pretty_bytes(X),
        "nopad": pretty_bytes(X, style="nopad"),
        "six": pretty_bytes(X, style="6"),
        "short": pretty_bytes([1337.0, 1.5e6, 0.0]),
        "inf_default": try_val(pretty_bytes, [INF, -INF]),
        "single": [pretty_bytes([1337.0])[0]],
    }


run_proof("pretty_bytes", one)
