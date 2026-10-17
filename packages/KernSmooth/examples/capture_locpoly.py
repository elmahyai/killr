"""Run the locpoly example in R and Python and save both plots."""

from __future__ import annotations

import subprocess
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "output"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    _python_plots()
    _r_plots()
    print("wrote the locpoly density and regression figures")


def _python_plots() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from kernsmooth import locpoly
    from mass import geyser

    sample = geyser["duration"]
    estimate = locpoly(sample, bandwidth=0.25)
    _figure, axes = plt.subplots()
    axes.plot(estimate["x"], estimate["y"])
    plt.savefig(OUTPUT / "locpoly-python-density.svg", format="svg")
    plt.close()

    waiting = geyser["waiting"]
    fit = locpoly(sample, waiting, bandwidth=0.25)
    _figure, axes = plt.subplots()
    axes.plot(sample, waiting, linestyle="none", marker="o")
    axes.plot(fit["x"], fit["y"])
    plt.savefig(OUTPUT / "locpoly-python-regression.svg", format="svg")
    plt.close()


def _r_plots() -> None:
    density = OUTPUT / "locpoly-r-density.svg"
    regression = OUTPUT / "locpoly-r-regression.svg"
    script = f"""
    svg("{density.as_posix()}", width=8, height=4.5)
    data(geyser, package="MASS")
    x <- geyser$duration
    est <- KernSmooth::locpoly(x, bandwidth=0.25)
    plot(est, type="l")
    dev.off()
    svg("{regression.as_posix()}", width=8, height=4.5)
    y <- geyser$waiting
    plot(x, y)
    fit <- KernSmooth::locpoly(x, y, bandwidth=0.25)
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
