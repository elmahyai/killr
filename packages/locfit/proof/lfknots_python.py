"""Python proof for locfit::lfknots against the R reference (locfit 1.5-9.12).

Run from the repository root after lfknots_r.R:
    python3 packages/locfit/proof/lfknots_python.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from locfit_proof_common import (check_case, load, new_state, read_fixture,  # noqa: E402
                                 read_r_output, read_r_timing, report, time_py_ms,
                                 to_plain, write_python_output)


def _what(value):
    return tuple(value) if isinstance(value, list) else (value,)


def main() -> None:
    lfknots = load("lfknots").lfknots
    cases = read_fixture("lfknots")["cases"]
    r_cases = read_r_output("lfknots")["cases"]
    total, lines, py_out = new_state(), [], {}
    for name, cs in cases.items():
        tr = np.exp if cs["tr"] == "exp" else None
        value = to_plain(lfknots(cs["fit"], tr=tr, what=_what(cs["what"]),
                                 delete_pv=bool(cs["delete_pv"])))
        py_out[name] = value
        check_case(name, r_cases[name], value, total, lines)
    write_python_output("lfknots", py_out)

    primary = cases["tree_default"]
    fit = primary["fit"]
    what = _what(primary["what"])
    py_ms = time_py_ms(lambda: lfknots(fit, what=what))
    r_ms = read_r_timing("lfknots")
    print(report("lfknots", lines, total, r_ms, py_ms))


if __name__ == "__main__":
    main()
