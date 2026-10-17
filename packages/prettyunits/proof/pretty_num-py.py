"""Proof: prettyunits.numbers.pretty_num against the R prettyunits 1.2.0 result."""

from harness import run_proof, try_val

from prettyunits.numbers import pretty_num

NAN = float("nan")
INF = float("inf")
Y = [None, NAN, -1.0, 0.0, 1e-25, 1.3333e-5, 999.0, 1000.0, 999950.0, 1e6, -2.5e9,
     1e30, 1e-30, 0.5, 1e-300, -1e-17]


def one():
    return {
        "default": pretty_num(Y),
        "nopad": pretty_num(Y, style="nopad"),
        "six": pretty_num(Y, style="6"),
        "docs": pretty_num([1337.0, 1.3333e-5, 13333337.0, 1333333337.0, 133333333337.0]),
        "inf_default": try_val(pretty_num, [INF, -INF]),
        "single": [pretty_num([1337.0])[0]],
    }


run_proof("pretty_num", one)
