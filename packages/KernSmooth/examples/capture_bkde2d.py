"""Run the bkde2D example in R and Python and save the contour and surface."""

from __future__ import annotations

import subprocess
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "output"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    _python_plots()
    _r_plots()
    print("wrote the bkde2D contour and surface figures")


def _python_plots() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from kernsmooth.bkde2d import bkde2d
    from mass import geyser

    sample = np.column_stack((geyser["duration"], geyser["waiting"]))
    estimate = bkde2d(sample, bandwidth=(0.7, 7.0))
    _figure, axes = plt.subplots()
    axes.contour(estimate["x1"], estimate["x2"], estimate["fhat"].T)
    plt.savefig(OUTPUT / "bkde2D-python-contour.svg", format="svg")
    plt.close()

    figure = plt.figure()
    axes = figure.add_subplot(projection="3d")
    grid1, grid2 = np.meshgrid(estimate["x1"], estimate["x2"], indexing="ij")
    axes.plot_surface(grid1, grid2, estimate["fhat"])
    plt.savefig(OUTPUT / "bkde2D-python-surface.svg", format="svg")
    plt.close()


def _r_plots() -> None:
    contour = OUTPUT / "bkde2D-r-contour.svg"
    surface = OUTPUT / "bkde2D-r-surface.svg"
    script = f"""
    svg("{contour.as_posix()}", width=8, height=4.5)
    data(geyser, package="MASS")
    x <- cbind(geyser$duration, geyser$waiting)
    est <- KernSmooth::bkde2D(x, bandwidth=c(0.7, 7))
    contour(est$x1, est$x2, est$fhat)
    dev.off()
    svg("{surface.as_posix()}", width=8, height=4.5)
    persp(est$fhat)
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
