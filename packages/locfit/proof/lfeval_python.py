"""Python proof for locfit::lfeval against the R reference (locfit 1.5-9.12).

Run from the repository root after lfeval_r.R:
    python3 packages/locfit/proof/lfeval_python.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from locfit_proof_common import (check_case, load, new_state, read_fixture,  # noqa: E402
                                 read_r_output, read_r_timing, report, time_py_ms,
                                 to_plain, write_python_output)


def main() -> None:
    lfeval = load("lfeval").lfeval
    fixtures = read_fixture("lfeval")["cases"]
    r_cases = read_r_output("lfeval")["cases"]
    total, lines, py_out = new_state(), [], {}
    for name, fit in fixtures.items():
        value = to_plain(lfeval(fit))
        py_out[name] = value
        check_case(name, r_cases[name], value, total, lines)
    write_python_output("lfeval", py_out)

    fit = fixtures["tree"]
    py_ms = time_py_ms(lambda: lfeval(fit))
    r_ms = read_r_timing("lfeval")
    print(report("lfeval", lines, total, r_ms, py_ms))


if __name__ == "__main__":
    main()
