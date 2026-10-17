"""Proof: prettyunits.ago.time_ago against the R prettyunits 1.2.0 result."""

from datetime import datetime, timedelta

from harness import run_proof, try_val

from prettyunits.ago import time_ago

# The offsets sit in the middle of each bucket, so the answer does not
# depend on the few milliseconds between the R and Python calls.
OFFSETS = [5, 30, 14 * 60, 5 * 3600, 25 * 3600, 5 * 86400, 30 * 86400,
           365 * 86400, 3650 * 86400]


def one():
    now = datetime.now()
    dates = [now - timedelta(seconds=s) for s in OFFSETS]
    return {
        "default": time_ago(dates),
        "short": time_ago(dates, format="short"),
        "terse": time_ago(dates, format="terse"),
        "bad_format": try_val(time_ago, now, format="nope"),
    }


run_proof("time_ago", one)
