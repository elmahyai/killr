"""Compare moments 0.14.1 with the installed R package."""

import json
import math
import subprocess

from moments import (
    Frame,
    Matrix,
    agostino_test,
    all_cumulants,
    all_moments,
    anscombe_test,
    bonett_test,
    central2raw,
    geary,
    jarque_test,
    kurtosis,
    moment,
    raw2central,
    skewness,
)

R = r"""
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(moments))
if (as.character(packageVersion("moments")) != "0.14.1") stop("expected 0.14.1")
tag <- function(x) {
  if (is.null(x)) return("NA")
  if (is.nan(x)) return("NaN")
  if (is.infinite(x)) return(if (x > 0) "Inf" else "-Inf")
  sprintf("%.17g", x)
}
flat <- function(x) {
  if (is.data.frame(x)) x <- as.matrix(x)
  if (is.list(x)) stop(paste("unexpected", paste(class(x), collapse = ",")))
  if (is.null(dim(x))) return(as.numeric(x))
  as.numeric(x)
}
cap <- function(expr) {
  warns <- character()
  val <- tryCatch(
    withCallingHandlers(expr, warning = function(w) {
      warns <<- c(warns, conditionMessage(w))
      invokeRestart("muffleWarning")
    }),
    error = function(e) structure(list(message = conditionMessage(e)), class = "err")
  )
  if (inherits(val, "err")) {
    return(list(error = val$message, warnings = warns))
  }
  if (inherits(val, "htest")) {
    return(list(
      error = "",
      values = vapply(c(as.numeric(val$statistic), val$p.value), tag, ""),
      names = c(names(val$statistic), "p"),
      alternative = val$alternative,
      method = val$method,
      warnings = warns
    ))
  }
  list(
    error = "",
    values = vapply(flat(val), tag, ""),
    names = if (is.null(names(val))) character() else names(val),
    colnames = if (is.null(colnames(val))) character() else colnames(val),
    class = paste(class(val), collapse = " "),
    alternative = "",
    method = "",
    warnings = warns
  )
}
set.seed(1)
y <- rnorm(30)
cases <- list(
  m_na = cap(moment(c(1, 2, NA, 4, -1))),
  m_rm = cap(moment(c(1, 2, NA, 4, -1), na.rm = TRUE)),
  m3 = cap(moment(c(1, 2, NA, 4, -1), order = 3, central = TRUE, na.rm = TRUE)),
  m0 = cap(moment(c(0, NA, 2), order = 0)),
  m_half = cap(moment(c(-2, 4), order = 1.5)),
  m_empty = cap(moment(numeric(0))),
  m_neg = cap(moment(c(-2, -1, 3), order = 3)),
  m_logi = cap(moment(c(TRUE, FALSE, TRUE))),
  skew = cap(skewness(c(1, 2, NA, 4, -1), na.rm = TRUE)),
  kurt = cap(kurtosis(c(1, 2, NA, 4, -1), na.rm = TRUE)),
  geary = cap(geary(c(1, 2, NA, 4, -1), na.rm = TRUE)),
  const = cap(skewness(c(2, 2, 2))),
  mat = cap(moment(matrix(c(1, 2, 3, 4, 5, 6), nrow = 3, dimnames = list(NULL, c("a", "b"))), order = 2, central = TRUE)),
  dfm = cap(moment(data.frame(a = c(1, 2, 3), b = c(4, 5, 6)))),
  allv = cap(all.moments(c(1, 2, 3, 4), order.max = 4)),
  allc = cap(all.moments(c(1, 2, 3, 4), order.max = 4, central = TRUE)),
  allm = cap(all.moments(matrix(c(1, 2, 3, 4, 5, 6), nrow = 3), order.max = 3)),
  alld = cap(all.moments(data.frame(a = 1:3, b = 4:6), order.max = 3, central = TRUE)),
  bad = cap(all.moments(1:5, order.max = 1)),
  r2c = cap(raw2central(all.moments(c(1, 2, 3, 4), order.max = 5))),
  c2r = cap(central2raw(all.moments(c(1, 2, 3, 4), central = TRUE, order.max = 5), mean(c(1, 2, 3, 4)))),
  cum = cap(all.cumulants(all.moments(c(1, 2, 3, 4), order.max = 5))),
  neg = cap(raw2central(all.moments(c(-2, -1, 0, 3, 4), order.max = 4))),
  long = cap(central2raw(all.moments(1:4, order.max = 3), c(1, 2))),
  ago = cap(agostino.test(y)),
  agol = cap(agostino.test(y, "l")),
  agog = cap(agostino.test(y, "greater")),
  ans = cap(anscombe.test(y)),
  ansl = cap(anscombe.test(y, "less")),
  bon = cap(bonett.test(y)),
  bong = cap(bonett.test(y, "g")),
  jar = cap(jarque.test(y)),
  n7 = cap(agostino.test(1:7)),
  n8 = cap(agostino.test(1:8)),
  alt = cap(agostino.test(1:20, "foo")),
  jarna = cap(jarque.test(c(1, 2, NA))),
  jarm = cap(jarque.test(matrix(1:6, nrow = 3))),
  jarc = cap(jarque.test(c("a", "b"))),
  iflong = cap(moment(1:4, central = c(TRUE, FALSE))),
  narm = cap(moment(1:3, na.rm = NA))
)
M <- matrix(c(1, 2, 3, 4, 5, 6), nrow = 3)
colnames(M) <- c("a", "b")
DF <- as.data.frame(all.moments(M, order.max = 4))
colnames(DF) <- c("a", "b")
cases$cumD <- cap(all.cumulants(DF))
cases$r2cD <- cap(raw2central(DF))
cent <- as.data.frame(raw2central(DF))
cases$c2rD <- cap(central2raw(cent, c(2, 5)))
cat(jsonlite::toJSON(cases, auto_unbox = FALSE, digits = 17))
"""


def run_r():
    path = "/tmp/moments_cases.R"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(R)
    proc = subprocess.run(["Rscript", path], check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr)
    return json.loads(proc.stdout)


def kind_of(value):
    if value is None:
        return "NA"
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    if isinstance(value, float) and math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    return f"{float(value):.17g}"


def flatten(value):
    if hasattr(value, "statistic"):
        numbers = list(value.statistic.values()) + [value.p_value]
        return [kind_of(item) for item in numbers]
    if isinstance(value, Matrix):
        out = []
        for column in value.columns:
            out.extend(kind_of(item) for item in column)
        return out
    if isinstance(value, Frame):
        out = []
        for column in value.columns:
            out.extend(kind_of(item) for item in column)
        return out
    if hasattr(value, "values"):
        return [kind_of(item) for item in value.values]
    if isinstance(value, list):
        return [kind_of(item) for item in value]
    return [kind_of(value)]


def text(expected, key):
    value = expected.get(key, "")
    if isinstance(value, list):
        return "" if not value else value[0]
    return value or ""


def check(name, expected, value):
    assert text(expected, "error") == "", (name, expected)
    got = flatten(value)
    want = expected["values"]
    assert len(got) == len(want), (name, got, want)
    for left, right in zip(got, want):
        if left in ("NA", "NaN", "Inf", "-Inf") or right in ("NA", "NaN", "Inf", "-Inf"):
            assert left == right, (name, got, want)
        else:
            assert abs(float(left) - float(right)) <= 1e-8, (name, got, want)
    print(name, "ok")


def check_error(name, expected, function):
    message = text(expected, "error")
    try:
        function()
    except (ValueError, IndexError, TypeError) as exc:
        assert message in str(exc), (name, str(exc), message)
        print(name, "ok")
        return
    raise AssertionError(name)


def main():
    expected = run_r()
    sample = [1, 2, None, 4, -1]
    check("m_na", expected["m_na"], moment(sample))
    check("m_rm", expected["m_rm"], moment(sample, na_rm=True))
    check("m3", expected["m3"], moment(sample, order=3, central=True, na_rm=True))
    check("m0", expected["m0"], moment([0, None, 2], order=0))
    check("m_half", expected["m_half"], moment([-2, 4], order=1.5))
    check("m_empty", expected["m_empty"], moment([]))
    check("m_neg", expected["m_neg"], moment([-2, -1, 3], order=3))
    check("m_logi", expected["m_logi"], moment([True, False, True]))
    check("skew", expected["skew"], skewness(sample, na_rm=True))
    check("kurt", expected["kurt"], kurtosis(sample, na_rm=True))
    check("geary", expected["geary"], geary(sample, na_rm=True))
    check("const", expected["const"], skewness([2, 2, 2]))
    columns = [[1, 2, 3], [4, 5, 6]]
    named = moment(Matrix(columns, ["a", "b"]), order=2, central=True)
    check("mat", expected["mat"], named)
    assert named.names == ["a", "b"]
    check("dfm", expected["dfm"], moment(Frame(columns, ["a", "b"])))
    check("allv", expected["allv"], all_moments([1, 2, 3, 4], order_max=4))
    check("allc", expected["allc"], all_moments([1, 2, 3, 4], order_max=4, central=True))
    check("allm", expected["allm"], all_moments(Matrix(columns), order_max=3))
    framed = all_moments(Frame(columns, ["a", "b"]), order_max=3, central=True)
    check("alld", expected["alld"], framed)
    assert isinstance(framed, Matrix) and framed.colnames is None
    check_error("bad", expected["bad"], lambda: all_moments([1, 2, 3, 4, 5], order_max=1))
    check("r2c", expected["r2c"], raw2central(all_moments([1, 2, 3, 4], order_max=5)))
    check(
        "c2r",
        expected["c2r"],
        central2raw(all_moments([1, 2, 3, 4], central=True, order_max=5), 2.5),
    )
    check("cum", expected["cum"], all_cumulants(all_moments([1, 2, 3, 4], order_max=5)))
    check("neg", expected["neg"], raw2central(all_moments([-2, -1, 0, 3, 4], order_max=4)))
    check_error(
        "long",
        expected["long"],
        lambda: central2raw(all_moments([1, 2, 3, 4], order_max=3), [1, 2]),
    )
    seed = json.loads(
        subprocess.run(
            [
                "Rscript",
                "-e",
                '.libPaths(c(path.expand("~/R/library"), .libPaths())); set.seed(1); cat(jsonlite::toJSON(rnorm(30), digits=17))',
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    check("ago", expected["ago"], agostino_test(seed))
    assert agostino_test(seed).alternative == "data have a skewness"
    less = agostino_test(seed, "l")
    check("agol", expected["agol"], less)
    assert less.alternative == "data have positive skewness"
    greater = agostino_test(seed, "greater")
    check("agog", expected["agog"], greater)
    assert greater.alternative == "data have negative skewness"
    check("ans", expected["ans"], anscombe_test(seed))
    check("ansl", expected["ansl"], anscombe_test(seed, "less"))
    check("bon", expected["bon"], bonett_test(seed))
    check("bong", expected["bong"], bonett_test(seed, "g"))
    assert bonett_test(seed, "g").alternative == "kurtosis is lower than sqrt(2/pi)"
    check("jar", expected["jar"], jarque_test(seed))
    check_error("n7", expected["n7"], lambda: agostino_test(list(range(1, 8))))
    check("n8", expected["n8"], agostino_test(list(range(1, 9))))
    check_error("alt", expected["alt"], lambda: agostino_test(list(range(1, 21)), "foo"))
    check("jarna", expected["jarna"], jarque_test([1, 2, None]))
    check_error("jarm", expected["jarm"], lambda: jarque_test(Matrix(columns)))
    check_error("jarc", expected["jarc"], lambda: jarque_test(["a", "b"]))
    check_error("iflong", expected["iflong"], lambda: moment([1, 2, 3, 4], central=[True, False]))
    check_error("narm", expected["narm"], lambda: moment([1, 2, 3], na_rm=None))
    raw = Frame(all_moments(Matrix(columns, ["a", "b"]), order_max=4).columns, ["a", "b"])
    cum = all_cumulants(raw)
    check("cumD", expected["cumD"], cum)
    assert isinstance(cum, Frame) and cum.colnames == ["X1", "X2"]
    converted = raw2central(raw)
    check("r2cD", expected["r2cD"], converted)
    assert isinstance(converted, Matrix) and converted.colnames == ["a", "b"]
    back = central2raw(Frame(converted.columns), [2, 5])
    check("c2rD", expected["c2rD"], back)
    assert isinstance(back, Frame) and back.colnames == ["X1", "X2"]
    print("ok")


if __name__ == "__main__":
    main()
