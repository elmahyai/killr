"""Run the dpik example in R and Python and save the line plots."""

from __future__ import annotations

import subprocess
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "output"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    _python_plot()
    _r_plot()
    print(f"wrote {OUTPUT / 'dpik-python.svg'} and {OUTPUT / 'dpik-r.svg'}")


def _python_plot() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from kernsmooth import bkde, dpik
    from mass import geyser

    sample = geyser["duration"]
    bandwidth = dpik(sample)
    estimate = bkde(sample, bandwidth=bandwidth)
    _figure, axes = plt.subplots()
    axes.plot(estimate["x"], estimate["y"])
    plt.savefig(OUTPUT / "dpik-python.svg", format="svg")
    plt.close()


def _r_plot() -> None:
    destination = OUTPUT / "dpik-r.svg"
    script = f"""
    svg("{destination.as_posix()}", width=8, height=4.5)
    data(geyser, package="MASS")
    x <- geyser$duration
    h <- KernSmooth::dpik(x)
    est <- KernSmooth::bkde(x, bandwidth=h)
    plot(est, type="l")
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
