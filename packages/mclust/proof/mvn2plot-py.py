"""Proof for mvn2plot: the ellipse, axes and centre R draws, logged in the shared format."""

from plot_fixtures import make_fixtures
from plot_proof_common import run_proof
from mclust.mvn2plot import mvn2plot

fx = make_fixtures()


def _window(ax, log):
    # The R cases first plot c(-2, 2) on c(-2, 2), so the ellipse is drawn in a known window.
    log.window(ax, (-2.0, 2.0), (-2.0, 2.0))


def default_case(fig, ax, log):
    _window(ax, log)
    mvn2plot(mu=fx["mu2"][:, 0], sigma=fx["sig2"][:, :, 0], ax=ax, log=log)


def fill_case(fig, ax, log):
    _window(ax, log)
    mvn2plot(mu=fx["mu2"][:, 1], sigma=fx["sig2"][:, :, 1], fillEllipse=True, ax=ax, log=log)


cases = {
    "default": default_case,
    "fill": fill_case,
    "alone": lambda fig, ax, log: mvn2plot(
        mu=fx["mu2"][:, 2], sigma=fx["sig2"][:, :, 2], alone=True, ax=ax, log=log),
}

if __name__ == "__main__":
    ms = run_proof("mvn2plot", cases, timed="default")
    print(f"mvn2plot python median ms {ms:.6g}")
