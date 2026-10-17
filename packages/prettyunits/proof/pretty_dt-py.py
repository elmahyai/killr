"""Proof: prettyunits.time.pretty_dt against the R prettyunits 1.2.0 result."""

from harness import run_proof, try_val

from prettyunits._difftime import Difftime
from prettyunits.time import pretty_dt

NAN = float("nan")
DT = Difftime(
    [1000.0, 0.0, 0.5, 59.99, 3600.0, 86400.0 * 3 + 5, None, NAN, -90.0,
     1e9, 1337.0, 0.9999, 2.5],
    units="secs",
)
DTM = Difftime([2.0, 1.5, 0.0], units="mins")


def one():
    return {
        "default": pretty_dt(DT),
        "compact": pretty_dt(DT, compact=True),
        "mins": pretty_dt(DTM),
        "mins_compact": pretty_dt(DTM, compact=True),
        "days": pretty_dt(Difftime(2.0, units="days")),
        "not_difftime": try_val(pretty_dt, 1000.0),
    }


run_proof("pretty_dt", one)
