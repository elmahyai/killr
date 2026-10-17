"""Compare modelr against the installed R package. Run with the project venv."""

from __future__ import annotations

import json
import math
import subprocess
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))

from boot.rng import set_seed
from modelr import (
    add_predictions,
    add_predictors,
    add_residuals,
    bootstrap,
    crossv_kfold,
    crossv_loo,
    crossv_mc,
    data_grid,
    fit_with,
    formulas,
    gather_predictions,
    gather_residuals,
    geom_ref_line,
    lm,
    mae,
    mape,
    model_matrix,
    mse,
    mtcars,
    na_warn,
    permute,
    predict,
    qae,
    resample,
    resample_bootstrap,
    resample_partition,
    resample_permutation,
    rmse,
    rsae,
    rsquare,
    seq_range,
    spread_predictions,
    spread_residuals,
    typical,
)
from modelr.datasets import iris
from modelr.formula import Env, Formula, Sym, merge_envs, parse_formula
from modelr.pretty import pretty
from modelr.quantile import quantile

ROOT = Path(__file__).resolve().parents[1]
R = r"""
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(modelr))
num <- function(x) sprintf("%.17g", as.numeric(x))
cat_num <- function(x) paste(vapply(x, num, ""), collapse = ",")
out <- list()
out$pretty <- list(
  a = pretty(c(0.25, 4.75), 3),
  b = pretty(c(1, 4), 10),
  c = pretty(c(-2.2, 0.4), 5),
  d = pretty(c(0, 1), 4),
  e = pretty(c(10, 10), 5)
)
x <- 1:4
out$seq <- list(
  n4 = seq_range(x, n = 4),
  pretty = seq_range(x, n = 3, expand = 0.5, pretty = TRUE),
  by = seq_range(x, by = 150, expand = 0.5, pretty = TRUE),
  trim = seq_range(x, n = 3, trim = 0.1)
)
out$q <- quantile(c(1, 2, 5, NA), c(0.05, 0.25, 0.5, 0.75, 0.95), na.rm = TRUE)
out$q1 <- as.numeric(quantile(c(1L, 2L, 3L, 8L), 0.5, type = 1, na.rm = TRUE))
mod <- lm(mpg ~ wt, data = mtcars)
out$coef <- unname(coef(mod))
out$pred <- unname(predict(mod, data.frame(wt = c(2, 3, 4))))
out$mse <- mse(mod, mtcars)
out$rmse <- rmse(mod, mtcars)
out$mae <- mae(mod, mtcars)
out$rsq <- rsquare(mod, mtcars)
out$mape <- mape(mod, mtcars)
out$rsae <- rsae(mod, mtcars)
out$qae <- unname(qae(mod, mtcars))
mm <- model.matrix(Sepal.Length ~ Species, data = iris)
out$sp <- lapply(c(1, 51, 101), function(i) as.numeric(mm[i, ]))
mm0 <- model.matrix(Sepal.Length ~ Species - 1, data = iris)
out$sp0 <- colnames(mm0)
fit <- fit_with(mtcars, lm, formulas(~disp,
  additive = ~drat + cyl,
  interaction = ~drat * cyl,
  full = add_predictors(interaction, ~am, ~vs)
))
out$full_names <- names(coef(fit$full))
out$full_coef <- unname(coef(fit$full))
set.seed(1)
out$boot <- as.integer(resample_bootstrap(mtcars))[1:8]
set.seed(1)
cv <- crossv_kfold(mtcars, 5)
out$fold <- as.integer(cv$test[[1]])
out$fold_id <- cv$.id
set.seed(1)
part <- resample_partition(mtcars, c(test = 0.3, train = 0.7))
out$part_test <- as.integer(part$test)
out$part_train_n <- length(as.integer(part$train))
set.seed(1)
perm <- resample_permutation(mtcars, "mpg")
out$perm <- as.integer(perm)[1:8]
df <- data.frame(x = 1:5, y = c(1, NA, 3, NA, 5))
m2 <- lm(y ~ x, data = df, na.action = na.warn)
out$na <- unname(predict(m2))
df2 <- data.frame(x = c(1, 2, NA), y = c(1.5, 2, 3.5))
mod2 <- lm(y ~ x, data = df2)
out$add <- unname(add_predictions(df2, mod2)$pred)
g <- data_grid(mtcars, vs, am)
out$grid <- c(g$vs, g$am)
mod3 <- lm(mpg ~ wt + cyl + vs, data = mtcars)
g2 <- data_grid(mtcars, .model = mod3)
out$g2 <- c(g2$wt, g2$cyl, g2$vs)
xx <- 1:10
yy <- xx + xx^2
pmod <- lm(yy ~ poly(xx, 2))
out$poly <- unname(residuals(pmod))
out$forms <- c(
  deparse(add_predictors(~1, ~2, ~3)),
  deparse(add_predictors(lhs ~ 1, ~2)),
  deparse(add_predictors(lhs ~ rhs, ~var1, ~var2, fun = "*")),
  deparse(formulas(~lhs, linear = ~var1 + var2, hierarchical = add_predictors(linear, ~(1 | group)))$hierarchical)
)
out$typ <- c(typical(c(1, 2, 5)), typical(c(1L, 2L, 3L, 8L)))
out$typc <- typical(c("a", "a", "b", "b"))
cat(jsonlite::toJSON(out, auto_unbox = TRUE, digits = 17))
"""


def r_value():
    script = Path("/tmp/modelr_cases.R")
    script.write_text(R, encoding="utf-8")
    proc = subprocess.run(["Rscript", str(script)], check=True, capture_output=True, text=True)
    text = proc.stdout.strip().splitlines()[-1]
    return json.loads(text)


def _missing(value):
    if value is None or value == "NA":
        return True
    return isinstance(value, float) and math.isnan(value)


def close(a, b, tol=1e-8):
    if isinstance(a, list) and not isinstance(b, list):
        b = [b]
    if isinstance(a, list):
        assert len(a) == len(b), (a, b)
        for left, right in zip(a, b):
            close(left, right, tol)
        return
    if _missing(a) or _missing(b):
        assert _missing(a) and _missing(b), (a, b)
        return
    assert abs(float(a) - float(b)) <= tol, (a, b, abs(float(a) - float(b)))


def test_against_r():
    try:
        import jsonlite  # noqa: F401
    except Exception:
        pass
    expected = r_value()
    close(pretty([0.25, 4.75], 3), expected["pretty"]["a"])
    close(pretty([1, 4], 10), expected["pretty"]["b"])
    close(pretty([-2.2, 0.4], 5), expected["pretty"]["c"])
    close(pretty([0, 1], 4), expected["pretty"]["d"])
    close(pretty([10, 10], 5), expected["pretty"]["e"])
    close(seq_range([1, 2, 3, 4], n=4), expected["seq"]["n4"])
    close(seq_range([1, 2, 3, 4], n=3, expand=0.5, pretty=True), expected["seq"]["pretty"])
    close(seq_range([1, 2, 3, 4], by=150, expand=0.5, pretty=True), expected["seq"]["by"])
    close(seq_range([1, 2, 3, 4], n=3, trim=0.1), expected["seq"]["trim"])
    close(quantile([1, 2, 5, None], [0.05, 0.25, 0.5, 0.75, 0.95], na_rm=True), expected["q"])
    close(quantile([1, 2, 3, 8], [0.5], type=1, na_rm=True), expected["q1"])
    model = lm("mpg ~ wt", mtcars)
    close(list(model.coefficients.values()), expected["coef"])
    close(predict(model, {"wt": [2, 3, 4]}), expected["pred"])
    close(mse(model, mtcars), expected["mse"])
    close(rmse(model, mtcars), expected["rmse"])
    close(mae(model, mtcars), expected["mae"])
    close(rsquare(model, mtcars), expected["rsq"])
    close(mape(model, mtcars), expected["mape"])
    close(rsae(model, mtcars), expected["rsae"])
    close(qae(model, mtcars), expected["qae"])
    matrix = model_matrix(iris, "Sepal.Length ~ Species")
    rows = [[matrix[name][row] for name in matrix.names()] for row in (0, 50, 100)]
    close(rows, expected["sp"])
    dropped = model_matrix(iris, "Sepal.Length ~ Species - 1")
    assert dropped.names() == expected["sp0"]
    fits = fit_with(
        mtcars,
        lm,
        formulas(
            "~disp",
            additive="~drat + cyl",
            interaction="~drat * cyl",
            full="add_predictors(interaction, '~am', '~vs')",
        ),
    )
    assert list(fits["full"].coefficients) == expected["full_names"]
    close(list(fits["full"].coefficients.values()), expected["full_coef"])
    set_seed(1)
    assert list(resample_bootstrap(mtcars).idx[:8]) == expected["boot"]
    set_seed(1)
    folds = crossv_kfold(mtcars, 5)
    assert folds["test"][0].idx == expected["fold"]
    assert folds[".id"] == expected["fold_id"]
    set_seed(1)
    part = resample_partition(mtcars, {"test": 0.3, "train": 0.7})
    assert part["test"].idx == expected["part_test"]
    assert len(part["train"].idx) == expected["part_train_n"]
    set_seed(1)
    assert resample_permutation(mtcars, ["mpg"]).idx[:8] == expected["perm"]
    warned = {"x": [1, 2, 3, 4, 5], "y": [1.0, None, 3.0, None, 5.0]}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fitted = lm("y ~ x", warned, na_action=na_warn)
    assert caught and "Dropping 2" in str(caught[0].message)
    close(predict(fitted), expected["na"])
    incomplete = {"x": [1.0, 2.0, None], "y": [1.5, 2.0, 3.5]}
    added = add_predictions(incomplete, lm("y ~ x", incomplete))
    close(added["pred"], expected["add"])
    grid = data_grid(mtcars, "vs", "am")
    close(grid["vs"] + grid["am"], expected["grid"])
    grid_model = data_grid(mtcars, model=lm("mpg ~ wt + cyl + vs", mtcars))
    close([grid_model["wt"][0], grid_model["cyl"][0], grid_model["vs"][0]], expected["g2"])
    poly_x = list(range(1, 11))
    poly_y = [value + value**2 for value in poly_x]
    poly_model = lm("yy ~ poly(xx, 2)", {"xx": poly_x, "yy": poly_y})
    from modelr.design import residuals as resid

    close(resid(poly_model, {"xx": poly_x, "yy": poly_y}), expected["poly"])
    assert str(add_predictors("~1", "~2", "~3")) == expected["forms"][0]
    assert str(add_predictors("lhs ~ 1", "~2")) == expected["forms"][1]
    assert str(add_predictors("lhs ~ rhs", "~var1", "~var2", fun="*")) == expected["forms"][2]
    made = formulas(
        "~lhs",
        linear="~var1 + var2",
        hierarchical="add_predictors(linear, '~(1 | group)')",
    )
    assert str(made["hierarchical"]) == expected["forms"][3]
    assert typical([1.0, 2.0, 5.0]) == expected["typ"][0]
    assert typical([1, 2, 3, 8]) == expected["typ"][1]
    assert typical(["a", "a", "b", "b"]) == expected["typc"]
    env = Env({"object": []}, parent=None)
    other = Env({"object": []}, parent=None)
    try:
        merge_envs(Formula(None, Sym("object"), env), Formula(None, Sym("object"), other))
    except ValueError as exc:
        assert "conflict for the symbol 'object'" in str(exc)
    else:
        raise AssertionError("expected a scope conflict")
    line = geom_ref_line(h=3)
    assert line.value == 3
    try:
        geom_ref_line()
    except ValueError as exc:
        assert "one of" in str(exc)
    else:
        raise AssertionError("expected a missing line")
    small = {"x": [1, 2, 3, 4, 5], "y": [1.0, 4.0, 3.0, 2.0, 5.0]}
    one = lm("y ~ x", small)
    two = lm("y ~ x", small)
    spread = spread_predictions(small, m1=one, m2=two)
    assert spread.names() == ["x", "y", "m1", "m2"]
    gathered = gather_predictions(small, m1=one, m2=two)
    assert gathered.names()[0] == "model"
    assert gathered.nrow == 10
    assert spread_residuals(small, m1=one, m2=two).names()[-2:] == ["m1", "m2"]
    assert gather_residuals(small, m1=one, m2=two).nrow == 10
    assert add_residuals(small, one).names()[-1] == "resid"
    set_seed(1)
    boot = bootstrap(mtcars, 4)
    assert boot.nrow == 4
    assert boot[".id"] == ["1", "2", "3", "4"]
    loo = crossv_loo(small)
    assert loo.nrow == 5
    assert loo[".id"] == [1, 2, 3, 4, 5]
    assert loo["test"][-1].idx == [5]
    set_seed(1)
    monte = crossv_mc(mtcars, 3, test=0.25)
    assert monte.nrow == 3
    drawn = resample(mtcars, list(range(1, 11)))
    assert "resample [10 x 11]" in str(drawn)
    assert str(permute(mtcars, 1, "mpg")["perm"][0]).startswith("<permutation (mpg)")
    print("ok")


if __name__ == "__main__":
    test_against_r()
