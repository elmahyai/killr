"""Run the dpill example in R and Python and save both plots."""

from __future__ import annotations

import subprocess
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "output"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    _python_plot()
    _r_plot()
    print("wrote the dpill regression figures")


def _python_plot() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from kernsmooth import locpoly
    from kernsmooth.dpill import dpill
    from mass import geyser

    duration = geyser["duration"]
    waiting = geyser["waiting"]
    bandwidth = dpill(duration, waiting)
    fit = locpoly(duration, waiting, bandwidth=bandwidth)
    _figure, axes = plt.subplots()
    axes.scatter(duration, waiting)
    axes.plot(fit["x"], fit["y"])
    plt.savefig(OUTPUT / "dpill-python.svg", format="svg")
    plt.close()


def _r_plot() -> None:
    destination = OUTPUT / "dpill-r.svg"
    script = f"""
    svg("{destination.as_posix()}", width=8, height=4.5)
    data(geyser, package="MASS")
    x <- geyser$duration
    y <- geyser$waiting
    plot(x, y)
    h <- KernSmooth::dpill(x, y)
    fit <- KernSmooth::locpoly(x, y, bandwidth=h)
    lines(fit)
    dev.off()
    """
    result = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)


if __name__ == "__main__":
    main()
