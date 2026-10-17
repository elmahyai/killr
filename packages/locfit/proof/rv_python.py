"""Python proof for locfit::rv against the R reference (locfit 1.5-9.12).

Run from the repository root after rv_r.R:
    python3 packages/locfit/proof/rv_python.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from locfit_proof_common import (check_case, load, new_state, read_fixture,  # noqa: E402
                                 read_r_output, read_r_timing, report, time_py_ms,
                                 to_plain, write_python_output)


def main() -> None:
    rv = load("rv").rv
    fixtures = read_fixture("rv")["cases"]
    r_cases = read_r_output("rv")["cases"]
    total, lines, py_out = new_state(), [], {}
    for name, fit in fixtures.items():
        value = to_plain(rv(fit))
        py_out[name] = value
        check_case(name, r_cases[name], value, total, lines)
    write_python_output("rv", py_out)

    fit = fixtures["tree"]
    py_ms = time_py_ms(lambda: rv(fit))
    r_ms = read_r_timing("rv")
    print(report("rv", lines, total, r_ms, py_ms))


if __name__ == "__main__":
    main()
