"""Python translation of tseries 0.10-63."""

import math
import sys

from tseries.datasets import NelPlo, USeconomic, bev, camp, ice_river, nino, tcm, tcmd
from tseries.finance import maxdrawdown, plot_ohlc, portfolio_optim, seqplot_ts, sharpe, sterling
from tseries.irts import (
    approx_irts,
    as_irts,
    daysecond,
    irts,
    is_businessday,
    is_irts,
    is_weekend,
    read_irts,
    subset_irts,
    value,
    weekday,
    write_irts,
)
from tseries.resample import na_remove, quadmap, read_matrix, read_ts, surrogate, tsbootstrap
from tseries.unitroot import (
    adf_test,
    bds_test,
    jarque_bera_test,
    kpss_test,
    po_test,
    pp_test,
    runs_test,
    terasvirta_test,
    white_test,
)


def garch_control(
    maxiter=200,
    trace=True,
    start=None,
    grad="analytical",
    abstol=None,
    reltol=None,
    xtol=None,
    falsetol=None,
    **qr,
):
    from tseries._num import match_arg

    eps = sys.float_info.epsilon
    if abstol is None:
        abstol = max(1e-20, eps**2)
    if reltol is None:
        reltol = max(1e-10, eps ** (2.0 / 3.0))
    if xtol is None:
        xtol = math.sqrt(eps)
    if falsetol is None:
        falsetol = 1e2 * eps
    return {
        "maxiter": maxiter,
        "trace": bool(trace),
        "start": start,
        "grad": match_arg(grad, ("analytical", "numerical")),
        "abstol": abstol,
        "reltol": reltol,
        "xtol": xtol,
        "falsetol": falsetol,
        "qr": dict(qr),
    }


from tseries.arma import arma


def garch(*_args, **_kwargs):
    raise NotImplementedError(
        "garch() fits the model with the PORT SUMSL routine in src/dsumsl.f. That optimiser is not translated."
    )


def get_hist_quote(*_args, **_kwargs):
    raise NotImplementedError(
        "get.hist.quote() downloads prices with quantmod::getSymbols and wraps them with zoo, which is not translated."
    )


__all__ = [
    "NelPlo",
    "USeconomic",
    "adf_test",
    "approx_irts",
    "arma",
    "as_irts",
    "bds_test",
    "bev",
    "camp",
    "daysecond",
    "garch",
    "garch_control",
    "get_hist_quote",
    "ice_river",
    "irts",
    "is_businessday",
    "is_irts",
    "is_weekend",
    "jarque_bera_test",
    "kpss_test",
    "maxdrawdown",
    "na_remove",
    "nino",
    "plot_ohlc",
    "po_test",
    "portfolio_optim",
    "pp_test",
    "quadmap",
    "read_irts",
    "read_matrix",
    "read_ts",
    "runs_test",
    "seqplot_ts",
    "sharpe",
    "sterling",
    "subset_irts",
    "surrogate",
    "tcm",
    "tcmd",
    "terasvirta_test",
    "tsbootstrap",
    "value",
    "weekday",
    "white_test",
    "write_irts",
]
