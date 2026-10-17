"""Proof for mclust2Dplot: the points, ellipses and error symbols, logged in the shared format."""

from plot_fixtures import make_fixtures
from plot_proof_common import run_proof
from mclust.mclust_2d_plot import mclust2Dplot

fx = make_fixtures()
P2 = {"mean": fx["mu2"], "variance": {"sigma": fx["sig2"]}}

cases = {
    "classification": lambda fig, ax, log: mclust2Dplot(
        fx["data2"], parameters=P2, classification=fx["cls"], ax=ax, log=log),
    "classification_fill": lambda fig, ax, log: mclust2Dplot(
        fx["data2"], parameters=P2, classification=fx["cls"], fillEllipses=True,
        ax=ax, log=log),
    "error": lambda fig, ax, log: mclust2Dplot(
        fx["data2"], parameters=P2, classification=fx["cls"], truth=fx["truth"],
        what="error", ax=ax, log=log),
    "uncertainty": lambda fig, ax, log: mclust2Dplot(
        fx["data2"], parameters=P2, z=fx["z"], what="uncertainty", ax=ax, log=log),
}

if __name__ == "__main__":
    ms = run_proof("mclust2Dplot", cases, timed="classification")
    print(f"mclust2Dplot python median ms {ms:.6g}")

    # Figure: the filled-ellipse case, saved as SVG next to the printed values.
    import matplotlib.pyplot as plt
    from plot_proof_common import OUT

    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(111)
    mclust2Dplot(fx["data2"], parameters=P2, classification=fx["cls"], fillEllipses=True, ax=ax)
    fig.savefig(OUT / "mclust2Dplot-classification_fill-python.svg", format="svg")
    plt.close(fig)
