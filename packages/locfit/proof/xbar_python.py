"""Python proof for locfit::xbar against the R reference (locfit 1.5-9.12).

Run from the repository root after xbar_r.R:
    python3 packages/locfit/proof/xbar_python.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from locfit_proof_common import (check_case, load, new_state, read_r_output,  # noqa: E402
                                 read_r_timing, report, time_py_ms, to_plain,
                                 write_python_output)


def main() -> None:
    xbar = load("xbar").xbar
    r_cases = read_r_output("xbar")["cases"]
    total, lines = new_state(), []
    value = to_plain(xbar())
    write_python_output("xbar", {"default": value})
    check_case("default", r_cases["default"], value, total, lines)

    py_ms = time_py_ms(xbar)
    r_ms = read_r_timing("xbar")
    print(report("xbar", lines, total, r_ms, py_ms))


if __name__ == "__main__":
    main()
