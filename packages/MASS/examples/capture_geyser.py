"""Run the geyser example in R and Python and save the printed durations."""

from __future__ import annotations

import subprocess
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "output"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    _python_print()
    _r_print()
    print(f"wrote {OUTPUT / 'geyser-python.txt'} and {OUTPUT / 'geyser-r.txt'}")


def _python_print() -> None:
    from mass import geyser

    (OUTPUT / "geyser-python.txt").write_text(repr(geyser["duration"]) + "\n")


def _r_print() -> None:
    script = """
    data(geyser, package="MASS")
    geyser$duration
    """
    result = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    (OUTPUT / "geyser-r.txt").write_text(result.stdout)


if __name__ == "__main__":
    main()
