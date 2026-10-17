"""Proof for clPairsLegend: the legend anchor, labels and symbols, logged in the shared format."""

from plot_proof_common import run_proof
from mclust.cl_pairs import clPairsLegend
from mclust.plot_log import PlotLog


def legend_case(fig, ax, log: PlotLog) -> None:
    # The R case first plots c(0, 1) on c(0, 1), which sets the window the legend uses.
    log.window(ax, (0.0, 1.0), (0.0, 1.0))
    clPairsLegend(0.1, 0.9, ["1", "2", "3"], col=["black", "red", "blue"],
                  pch=[1, 2, 3], cex=1.0, ax=ax, log=log)


cases = {"legend": legend_case}

if __name__ == "__main__":
    ms = run_proof("clPairsLegend", cases, timed="legend")
    print(f"clPairsLegend python median ms {ms:.6g}")
