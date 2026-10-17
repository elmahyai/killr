"""Proof: prettyunits.p_value.pretty_p_value against the R prettyunits 1.2.0 result."""

from harness import run_proof, try_val

from prettyunits.p_value import pretty_p_value

NAN = float("nan")
X = [1.0, 0.0, None, 0.01, 0.0000001, 0.0001, 0.00015, 0.5, 0.99995,
     0.00009999, NAN, 0.123456]


def one():
    return {
        "default": pretty_p_value(X),
        "minval_05": pretty_p_value(X, minval=0.05),
        "minval_001": pretty_p_value(X, minval=0.001),
        "all_na": pretty_p_value([None, None]),
        "out_of_range": try_val(pretty_p_value, [1.5]),
        "bad_minval": try_val(pretty_p_value, [0.5], minval=1.0),
    }


run_proof("pretty_p_value", one)
