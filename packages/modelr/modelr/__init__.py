"""Python translation of the R package modelr."""

from modelr.augment import (
    add_predictions,
    add_residuals,
    gather_predictions,
    gather_residuals,
    spread_predictions,
    spread_residuals,
)
from modelr.datasets import heights, iris, mtcars, sim1, sim2, sim3, sim4
from modelr.design import lm, model_matrix, na_exclude, na_omit, na_warn, predict, predictor_vars, residuals, response, response_var
from modelr.formula import add_predictors, fit_with, formulae, formulas
from modelr.geom import geom_ref_line
from modelr.grid import data_grid
from modelr.pipe import pipe
from modelr.quality import mae, mape, mse, qae, rmse, rsae, rsquare
from modelr.resample import (
    bootstrap,
    crossv_kfold,
    crossv_loo,
    crossv_mc,
    permute,
    permute_,
    resample,
    resample_bootstrap,
    resample_partition,
    resample_permutation,
)
from modelr.seq_range import seq_range
from modelr.typical import typical

__all__ = [
    "add_predictions",
    "add_predictors",
    "add_residuals",
    "bootstrap",
    "crossv_kfold",
    "crossv_loo",
    "crossv_mc",
    "data_grid",
    "fit_with",
    "formulae",
    "formulas",
    "gather_predictions",
    "gather_residuals",
    "geom_ref_line",
    "heights",
    "iris",
    "lm",
    "mae",
    "mape",
    "model_matrix",
    "mse",
    "mtcars",
    "na_exclude",
    "na_omit",
    "na_warn",
    "permute",
    "permute_",
    "pipe",
    "predict",
    "predictor_vars",
    "qae",
    "resample",
    "resample_bootstrap",
    "resample_partition",
    "resample_permutation",
    "residuals",
    "response",
    "response_var",
    "rmse",
    "rsae",
    "rsquare",
    "seq_range",
    "sim1",
    "sim2",
    "sim3",
    "sim4",
    "spread_predictions",
    "spread_residuals",
    "typical",
]
