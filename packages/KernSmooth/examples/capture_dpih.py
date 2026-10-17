"""Run the dpih example in R and Python and save the histograms."""

from __future__ import annotations

import subprocess
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "output"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    _python_plot()
    _r_plot()
    print(f"wrote {OUTPUT / 'dpih-python.svg'} and {OUTPUT / 'dpih-r.svg'}")


def _python_plot() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from kernsmooth import dpih
    from kernsmooth.dpih import histogram_breaks
    from mass import geyser

    sample = geyser["duration"]
    width = dpih(sample)
    _figure, axes = plt.subplots()
    axes.hist(sample, bins=histogram_breaks(sample, width))
    plt.savefig(OUTPUT / "dpih-python.svg", format="svg")
    plt.close()


def _r_plot() -> None:
    destination = OUTPUT / "dpih-r.svg"
    script = f"""
    svg("{destination.as_posix()}", width=8, height=4.5)
    data(geyser, package="MASS")
    x <- geyser$duration
    h <- KernSmooth::dpih(x)
    bins <- seq(min(x) - h, max(x) + h, by = h)
    hist(x, breaks = bins)
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
