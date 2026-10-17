"""Run the bkfe example in R and Python and save the printed number."""

from __future__ import annotations

import subprocess
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "output"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    _python_print()
    _r_print()
    print(f"wrote {OUTPUT / 'bkfe-python.txt'} and {OUTPUT / 'bkfe-r.txt'}")


def _python_print() -> None:
    from kernsmooth import bkfe
    from mass import geyser

    estimate = bkfe(geyser["duration"], drv=4, bandwidth=0.3)
    (OUTPUT / "bkfe-python.txt").write_text(repr(estimate) + "\n")


def _r_print() -> None:
    script = """
    data(geyser, package="MASS")
    x <- geyser$duration
    est <- KernSmooth::bkfe(x, drv=4, bandwidth=0.3)
    est
    """
    result = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    (OUTPUT / "bkfe-r.txt").write_text(result.stdout)


if __name__ == "__main__":
    main()
