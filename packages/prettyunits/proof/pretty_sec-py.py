"""Proof: prettyunits.time.pretty_sec against the R prettyunits 1.2.0 result."""

from harness import run_proof

from prettyunits.time import pretty_sec

NAN = float("nan")
SEC = [0.0, 0.0004, 0.9999, 1.337, 13.37, 133.7, 1337.0, 13370.0, 133700.0,
       1337000.0, 13370000.0, -2.5, None, NAN, 86400.0 * 1.5, 59.96,
       -2.601329396065269e+16, -1.3009319809382128e-23]


def one():
    return {
        "default": pretty_sec(SEC),
        "compact": pretty_sec(SEC, compact=True),
    }


run_proof("pretty_sec", one)
