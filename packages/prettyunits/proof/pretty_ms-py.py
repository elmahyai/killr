"""Proof: prettyunits.time.pretty_ms against the R prettyunits 1.2.0 result."""

from harness import run_proof

from prettyunits.time import pretty_ms

NAN = float("nan")
MS = [0.0, 0.4, 999.9999, 1000.0, 1337.0, 13370.0, 133700.0, 1337000.0,
      1337000000.0, -5.0, None, NAN, 2 * 86400000.0 + 5 * 3600000.0 + 7 * 60000.0 + 1234.5,
      59999.96, 3599999.9, 86400000.0, 1.0, 6.445565082178481e+20, -3.231135713311895e-24]


def one():
    return {
        "default": pretty_ms(MS),
        "compact": pretty_ms(MS, compact=True),
    }


run_proof("pretty_ms", one)
