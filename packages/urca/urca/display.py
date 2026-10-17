"""``show``, ``summary``, and ``plot`` methods for urca test objects."""

from __future__ import annotations

import io
import math
import sys
from contextlib import redirect_stdout

import numpy as np

from urca.ca_po import CaPo
from urca.johansen import CaJo, CaJoTest
from urca.plotres import _acf, _data_limit, _pacf, _padded, _stem
from urca.tests import UnitRoot
from urca.ur_ers import UrErs
from urca.ur_sp import UrSp
from urca.ur_za import UrZa


class SumUrca:
    """Printed summary object (R ``sumurca``)."""

    def __init__(self, **fields):
        self.__dict__.update(fields)


class PlotUrca:
    """Numeric series drawn by ``plot`` (for proofs)."""

    def __init__(self, values, figures=None):
        self.values = values
        self.figures = figures or []


def summary(object):
    """Build a ``sumurca`` object from a urca test fit."""
    if isinstance(object, SumUrca):
        return object
    if isinstance(object, UrErs):
        return SumUrca(
            classname="ur.ers",
            test_name=object.test_name,
            testreg=object.testreg,
            teststat=object.teststat,
            cval=object.cval,
            model=object.model,
            type=object.type,
        )
    if isinstance(object, CaJo):
        return SumUrca(
            classname="ca.jo",
            test_name=object.test_name,
            teststat=object.teststat,
            cval=object.cval,
            model=object.model,
            type=object.type,
            lambda_=object.lambda_,
            V=object.V,
            W=object.W,
            P=object.P,
        )
    if isinstance(object, CaJoTest):
        return SumUrca(
            classname="cajo.test",
            test_name=object.test_name,
            teststat=object.teststat,
            type=object.type,
            H=getattr(object, "H", None),
            A=getattr(object, "A", None),
            lambda_=object.lambda_,
            pval=object.pval,
            V=object.V,
            W=object.W,
        )
    if isinstance(object, UnitRoot) and object.test_name == "KPSS":
        return SumUrca(
            classname="ur.kpss",
            test_name=object.test_name,
            teststat=object.teststat,
            cval=object.cval,
            type=object.type,
            lag=object.lag,
        )
    if isinstance(object, CaPo):
        return SumUrca(
            classname="ca.po",
            test_name=object.test_name,
            testreg=object.testreg,
            teststat=object.teststat,
            cval=object.cval,
            model=object.model,
            type=object.type,
        )
    if isinstance(object, UnitRoot) and object.test_name == "Phillips-Perron":
        return SumUrca(
            classname="ur.pp",
            test_name=object.test_name,
            testreg=getattr(object, "testreg", None),
            teststat=object.teststat,
            cval=object.cval,
            model=object.model,
            type=object.type,
            auxstat=getattr(object, "auxstat", None),
        )
    if isinstance(object, UnitRoot) and object.test_name == "Augmented Dickey-Fuller Test":
        return SumUrca(
            classname="ur.df",
            test_name=object.test_name,
            testreg=object.testreg,
            teststat=object.teststat,
            cval=object.cval,
            model=object.model,
            test_names=object.test_names,
        )
    if isinstance(object, UrSp):
        return SumUrca(
            classname="ur.sp",
            test_name=object.test_name,
            testreg=object.testreg,
            teststat=object.teststat,
            cval=object.cval,
            signif=object.signif,
        )
    if isinstance(object, UrZa):
        return SumUrca(
            classname="ur.za",
            test_name=object.test_name,
            testreg=object.testreg,
            teststat=object.teststat,
            cval=object.cval,
            bpoint=object.bpoint,
        )
    raise TypeError(f"no summary method for object of class {type(object).__name__}")


def show(object):
    """Print a urca object or its ``sumurca`` summary."""
    if isinstance(object, SumUrca):
        _show_sumurca(object)
        return object
    if _is_short_show(object):
        _show_urca_short(object)
        return object
    raise TypeError(f"no show method for object of class {type(object).__name__}")


def show_text(object):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        show(object)
    return buffer.getvalue().rstrip("\n")


def plot(x, y=None):
    """Diagnostic plots for urca test objects."""
    del y
    if isinstance(x, UrErs):
        return _plot_ur_ers(x)
    if isinstance(x, CaJo):
        return _plot_ca_jo(x)
    if isinstance(x, UnitRoot) and x.test_name == "KPSS":
        return _plot_ur_kpss(x)
    if isinstance(x, CaPo):
        return _plot_ca_po(x)
    if isinstance(x, UnitRoot) and x.test_name == "Phillips-Perron":
        return _plot_ur_pp(x)
    if isinstance(x, UnitRoot) and x.test_name == "Augmented Dickey-Fuller Test":
        return _plot_ur_df(x)
    if isinstance(x, UrSp):
        return _plot_ur_sp(x)
    if isinstance(x, UrZa):
        return _plot_ur_za(x)
    raise TypeError(f"no plot method for object of class {type(x).__name__}")


def plot_values(x, y=None):
    """Numeric values underlying ``plot`` (residuals, acf, pacf, limits)."""
    del y
    result = plot(x)
    return np.asarray(result.values, dtype=float)


def _is_short_show(obj):
    return isinstance(obj, (CaJo, CaJoTest, CaPo, UrErs, UrSp, UrZa, UnitRoot))


def _banner(title):
    row = "#" * len(title)
    print()
    print(row)
    print(title)
    print(row)
    print()


def _round4(value):
    return f"{round(float(value), 4):.4f}"


def _format_pvalue(value):
    return f"{float(value):.5f}".rstrip("0").rstrip(".")


def _show_urca_short(obj):
    title = f"# {obj.test_name} Unit Root / Cointegration Test #"
    _banner(title)
    stats = np.ravel(np.asarray(obj.teststat, dtype=float))
    shown = " ".join(_round4(value) for value in stats)
    print(f"The value of the test statistic is: {shown} ")
    print()
    print()


def _show_sumurca(obj):
    name = obj.classname
    if name == "ur.df":
        _show_ur_df_summary(obj)
    elif name == "ur.kpss":
        _show_ur_kpss_summary(obj)
    elif name == "ca.jo":
        _show_ca_jo_summary(obj)
    elif name == "cajo.test":
        _show_cajo_test_summary(obj)
    elif name == "ca.po":
        _show_ca_po_summary(obj)
    elif name == "ur.pp":
        _show_ur_pp_summary(obj)
    elif name == "ur.sp":
        _show_ur_sp_summary(obj)
    elif name == "ur.za":
        _show_ur_za_summary(obj)
    elif name == "ur.ers":
        _show_ur_ers_summary(obj)
    else:
        raise TypeError(f"no show method for sumurca class {name!r}")


def _show_ur_df_summary(obj):
    title = f"# {obj.test_name} Unit Root Test #"
    _banner(title)
    print(f"Test regression {obj.model} ")
    print()
    _print_testreg(obj.testreg)
    print()
    stats = np.ravel(np.asarray(obj.teststat, dtype=float))
    shown = " ".join(_round4(value) for value in stats)
    print(f"Value of test-statistic is: {shown} ")
    print()
    print("Critical values for test statistics: ")
    _print_cval_matrix(obj.cval, obj.test_names)
    print()


def _cval_row_names(obj):
    if hasattr(obj, "cval_names"):
        return list(obj.cval_names)
    rows = np.asarray(obj.cval, dtype=float)
    if rows.ndim == 1:
        return ["tau1"]
    return [f"row{i + 1}" for i in range(rows.shape[0])]


def _show_ur_kpss_summary(obj):
    title = f"# {obj.test_name} Unit Root Test #"
    _banner(title)
    print(f"Test is of type: {obj.type} with {obj.lag} lags. ")
    print()
    print(f"Value of test-statistic is: {_round4(obj.teststat[0])} ")
    print()
    print("Critical value for a significance level of: ")
    _print_cval_matrix(obj.cval, obj.cval_names if hasattr(obj, "cval_names") else ["critical values"])
    print()


def _show_ca_jo_summary(obj):
    title = f"# {obj.test_name} #"
    _banner(title)
    print(f"Test type: {obj.type} , {obj.model} ")
    print()
    print("Eigenvalues (lambda):")
    print(np.asarray(obj.lambda_, dtype=float))
    print()
    cval = obj.cval
    if cval is not None:
        stats = np.round(np.asarray(obj.teststat, dtype=float), 2)
        if stats.ndim == 1:
            stats = stats.reshape(-1, 1)
        header = ["test", "1pct", "5pct", "10pct"]
        _print_matrix(stats, cval, header, row_labels=None)
        print()
    else:
        print("Values of test statistic")
        print()
        p = int(obj.P)
        labels = [f"r <= {rank}  |" for rank in range(p - 1, 0, -1)] + ["r = 0  |"]
        _print_column(np.asarray(obj.teststat, dtype=float), labels)
        print()
    print("Eigenvectors, normalised to first column:")
    print("(These are the cointegration relations)")
    print()
    print(np.asarray(obj.V, dtype=float))
    print()
    print("Weights W:")
    print("(This is the loading matrix)")
    print()
    print(np.asarray(obj.W, dtype=float))
    print()


def _show_cajo_test_summary(obj):
    title = f"# {obj.test_name} #"
    _banner(title)
    print(obj.type)
    print()
    print("The VECM has been estimated subject to: ")
    print("beta=H*phi and/or alpha=A*psi")
    if getattr(obj, "H", None) is not None:
        print()
        print(np.asarray(obj.H, dtype=float))
        print()
    if getattr(obj, "A", None) is not None:
        print()
        print(np.asarray(obj.A, dtype=float))
        print()
    print("Eigenvalues of restricted VAR (lambda):")
    print(np.round(np.asarray(obj.lambda_, dtype=float), 4))
    print()
    print("The value of the likelihood ratio test statistic:")
    print(f"{round(float(obj.teststat), 2):g} distributed as chi square with {obj.pval[1]} df.")
    print(f"The p-value of the test statistic is: {round(float(obj.pval[0]), 2):g} ")
    print()
    print("Eigenvectors, normalised to first column")
    print("of the restricted VAR:")
    print()
    print(np.round(np.asarray(obj.V, dtype=float), 4))
    print()
    print("Weights W of the restricted VAR:")
    print()
    print(np.round(np.asarray(obj.W, dtype=float), 4))
    print()


def _show_ca_po_summary(obj):
    title = f"# {obj.test_name} Unit Root Test #"
    _banner(title)
    print(f"Test of type {obj.type} ")
    print(f"detrending of series {obj.model} ")
    print()
    _print_ca_po_testreg(obj.testreg)
    print()
    print(f"Value of test-statistic is: {round(float(obj.teststat), 4):g} ")
    print()
    print(f"Critical values of {obj.type} are:")
    print(np.asarray(obj.cval, dtype=float))
    print()


def _show_ur_pp_summary(obj):
    title = f"# {obj.test_name} Unit Root Test #"
    _banner(title)
    print(f"Test regression {obj.model} ")
    print()
    if obj.testreg is not None:
        _print_testreg(obj.testreg)
        print()
    print(f"Value of test-statistic, type: {obj.type} is: {round(float(obj.teststat[0]), 4):g} ")
    print()
    if getattr(obj, "auxstat", None) is not None:
        print(np.asarray(obj.auxstat, dtype=float))
        print()
    if obj.type == "Z-tau":
        print("Critical values for Z statistics: ")
        print(np.asarray(obj.cval, dtype=float))
        print()


def _show_ur_sp_summary(obj):
    title = f"# {obj.test_name} Unit Root Test #"
    _banner(title)
    _print_testreg(obj.testreg)
    print()
    print(f"Value of test-statistic is: {round(float(obj.teststat), 4):g} ")
    print()
    print(f"Critical value for a significance level of {obj.signif} ")
    print(f"is: {obj.cval} ")
    print()


def _show_ur_za_summary(obj):
    title = f"# {obj.test_name} Unit Root Test #"
    _banner(title)
    _print_testreg(obj.testreg)
    print()
    print(f"Teststatistic: {round(float(obj.teststat), 4):g} ")
    cval = np.ravel(np.asarray(obj.cval, dtype=float))
    print(f"Critical values: 0.01= {cval[0]} 0.05= {cval[1]} 0.1= {cval[2]} ")
    print()
    print(f"Potential break point at position: {obj.bpoint} ")
    print()


def _show_ur_ers_summary(obj):
    title = f"# {obj.test_name} Unit Root Test #"
    _banner(title)
    print(f"Test of type {obj.type} ")
    print(f"detrending of series {obj.model} ")
    print()
    if obj.testreg is not None:
        _print_testreg(obj.testreg)
        print()
    print(f"Value of test-statistic is: {round(float(obj.teststat), 4):g} ")
    print()
    print(f"Critical values of {obj.type} are:")
    print(np.asarray(obj.cval, dtype=float))
    print()


def _print_testreg(testreg):
    if isinstance(testreg, dict) and "formula" in testreg:
        _print_summary_lm(testreg)
    elif isinstance(testreg, list):
        _print_ca_po_testreg(testreg)
    else:
        print(testreg)


def _print_ca_po_testreg(testreg):
    for block in testreg:
        table = np.asarray(block["coefficients"], dtype=float)
        print(table)


def _print_summary_lm(testreg):
    fit = testreg["fit"]
    response = np.asarray(testreg["response"], dtype=float)
    coef_names = list(testreg["coef_names"])
    formula = testreg["formula"]
    residuals = np.asarray(fit["residuals"], dtype=float)
    print()
    print("Call:")
    print(f"lm(formula = {formula})")
    print()
    print("Residuals:")
    print(_five_number(residuals))
    print()
    print("Coefficients:")
    pvals = _two_sided_p(fit["t"], fit["df"])
    rows = []
    for index, name in enumerate(coef_names):
        stars = _signif_code(pvals[index])
        rows.append(
            (
                name,
                float(fit["coef"][index]),
                float(fit["se"][index]),
                float(fit["t"][index]),
                float(pvals[index]),
                stars,
            )
        )
    _print_coef_table(rows)
    print("---")
    print("Signif. codes:  0 ‘***’ 0.001 ‘**’ 0.01 ‘*’ 0.05 ‘.’ 0.1 ‘ ’ 1")
    print()
    rss = float(fit["rss"])
    df = int(fit["df"])
    sigma = math.sqrt(rss / df) if df > 0 else float("nan")
    n = response.size
    tss = float(np.dot(response - response.mean(), response - response.mean()))
    r2 = 1.0 - rss / tss if tss > 0 else float("nan")
    adj = 1.0 - (1.0 - r2) * (n - 1) / df if df > 0 else float("nan")
    p = len(coef_names)
    fstat = ((tss - rss) / (p - 1)) / (rss / df) if p > 1 and df > 0 else float("nan")
    fpval = _f_pvalue(fstat, p - 1, df) if p > 1 and df > 0 else float("nan")
    print(f"Residual standard error: {sigma:.3f} on {df} degrees of freedom")
    print(f"Multiple R-squared:  {r2:.4f},\tAdjusted R-squared:  {adj:.5g} ")
    if p > 1:
        print(f"F-statistic: {fstat:.3f} on {p - 1} and {df} DF,  p-value: {_format_pvalue(fpval)}")
    print()


def _five_number(values):
    parts = np.percentile(values, [0, 25, 50, 75, 100])
    header = "    Min      1Q  Median      3Q     Max "
    nums = " ".join(f"{part:.4f}" for part in parts)
    return f"{header}\n{nums} "


def _print_coef_table(rows):
    print("            Estimate Std. Error t value Pr(>|t|)  ")
    for name, est, se, tval, pval, stars in rows:
        print(f"{name:<12}{est:7.5f}    {se:7.5f}   {tval:5.3f}   {pval:6.4f}{stars}")


def _signif_code(pval):
    if pval < 0.001:
        return " ***"
    if pval < 0.01:
        return " **"
    if pval < 0.05:
        return " *"
    if pval < 0.1:
        return " ."
    return "  "


def _two_sided_p(tvals, df):
    from scipy.stats import t as student_t

    out = []
    for value in np.asarray(tvals, dtype=float).ravel():
        out.append(2.0 * student_t.sf(abs(value), df))
    return np.asarray(out, dtype=float)


def _f_pvalue(fstat, df1, df2):
    from scipy.stats import f

    return float(f.sf(fstat, df1, df2))


def _print_cval_matrix(cval, row_names):
    rows = np.asarray(cval, dtype=float)
    if rows.ndim == 1:
        rows = rows.reshape(1, -1)
    print("      1pct  5pct 10pct")
    for label, row in zip(row_names, rows):
        print(f"{label:4} " + " ".join(f"{value:5.2f}" for value in row))


def _print_matrix(stats, cval, header, row_labels):
    cval_arr = np.asarray(cval, dtype=float)
    if cval_arr.ndim == 1:
        cval_arr = cval_arr.reshape(1, -1)
    combined = np.column_stack((stats, cval_arr))
    print(" ".join(f"{name:>6}" for name in header))
    for index, row in enumerate(combined):
        label = "" if row_labels is None else row_labels[index]
        prefix = f"{label} " if label else ""
        print(prefix + " ".join(f"{value:6.2f}" for value in row))


def _print_column(values, labels):
    for label, value in zip(labels, np.ravel(values)):
        print(f"{label} {value:.6g}")


def _plot_ur_df(obj):
    res = np.asarray(obj.res, dtype=float)
    return _plot_residual_acf(res)


def _plot_ur_kpss(obj):
    res = np.asarray(obj.res, dtype=float)
    return _plot_residual_acf(res, title=f"Residuals from test regression of type:{obj.type} with{obj.lag}lags")


def _plot_ur_pp(obj):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    y = np.asarray(obj.y, dtype=float)
    res = np.asarray(obj.res, dtype=float)
    fitted = y - res
    pieces = [y[1:], fitted[1:], res, *_acf_pacf_values(res)]
    figure = plt.figure(figsize=(7, 7))
    grid = figure.add_gridspec(3, 2)
    ax1 = figure.add_subplot(grid[0, :])
    ax1.plot(np.arange(1, y.size), y[1:], color="black")
    ax1.plot(np.arange(1, y.size), fitted[1:], color="seagreen")
    ax1.set_title(f"Diagram of fit for model {obj.model} ")
    _residual_panels(figure, grid, res, start_row=1)
    figure.tight_layout()
    return PlotUrca(np.concatenate(pieces), [figure])


def _plot_ur_sp(obj):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    y = np.asarray(obj.y, dtype=float)
    res = np.asarray(obj.res, dtype=float)
    pieces = [y[1:], y[1:] - res, res, *_acf_pacf_values(res)]
    figure = plt.figure(figsize=(7, 7))
    grid = figure.add_gridspec(3, 2)
    ax1 = figure.add_subplot(grid[0, :])
    ax1.plot(np.arange(1, y.size - 1), y[1:-1], color="black")
    ax1.plot(np.arange(1, y.size - 1), y[1:-1] - res, color="seagreen")
    ax1.set_title(f"Diagram of fit for model with polynomial degree of  {obj.polynomial}")
    _residual_panels(figure, grid, res, start_row=1)
    figure.tight_layout()
    return PlotUrca(np.concatenate(pieces), [figure])


def _plot_ur_ers(obj):
    if obj.testreg is None:
        raise ValueError("No plot method for P-test available")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    diff = np.diff(np.asarray(obj.yd, dtype=float))
    used = diff[obj.lag :]
    resid = np.asarray(obj.testreg["residuals"], dtype=float)
    fitted = used - resid
    pieces = [used, fitted, resid, *_acf_pacf_values(resid)]
    figure = plt.figure(figsize=(7, 7))
    grid = figure.add_gridspec(3, 2)
    ax1 = figure.add_subplot(grid[0, :])
    ax1.plot(used, color="black")
    ax1.plot(fitted, color="seagreen")
    ax1.set_title(
        "Diagram of fit for test regression\n"
        f"detrending {obj.model} and {obj.lag} lagged differences used in test regression",
    )
    _residual_panels(figure, grid, resid, start_row=1)
    figure.tight_layout()
    return PlotUrca(np.concatenate(pieces), [figure])


def _plot_ca_jo(obj):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = np.asarray(obj.x, dtype=float)
    v = np.asarray(obj.V, dtype=float)
    if obj.P == v.shape[0]:
        ci = x @ v
    else:
        ci = x @ v[: obj.P]
    figures = []
    pieces = []
    for index in range(int(obj.P)):
        series = x[:, index]
        coint = ci[:, index]
        pieces.extend([series, coint])
        figure, axes = plt.subplots(2, 1, figsize=(7, 5))
        axes[0].plot(series, color="black")
        axes[0].set_title(f"Time series plot of y{index + 1}")
        axes[1].plot(coint, color="black")
        axes[1].set_title(f"Cointegration relation of {index + 1}. variable")
        figure.tight_layout()
        figures.append(figure)
        if sys.stdin.isatty() and sys.stdout.isatty():
            print("\nType <Return> to continue: ", end="", flush=True)
            sys.stdin.readline()
    return PlotUrca(np.concatenate(pieces), figures)


def _plot_ca_po(obj):
    res = np.asarray(obj.res, dtype=float)
    if obj.type == "Pu":
        return _plot_residual_acf(res[:, 0], title="Residuals of CI-regression for y1")
    figures = []
    pieces = []
    for index in range(res.shape[1]):
        column = res[:, index]
        drawn = _plot_residual_acf(column, title=f"Residuals of CI-regression with y{index + 1} as lhs")
        pieces.append(drawn.values)
        figures.extend(drawn.figures)
        if sys.stdin.isatty() and sys.stdout.isatty():
            print("\nType <Return> to continue: ", end="", flush=True)
            sys.stdin.readline()
    return PlotUrca(np.concatenate(pieces), figures)


def _plot_ur_za(obj):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tstats = np.asarray(obj.tstats, dtype=float)
    cval = np.asarray(obj.cval, dtype=float)
    yvals = np.sort(np.concatenate([cval, tstats]))
    n = len(obj.y)
    figure, ax = plt.subplots()
    ax.plot(tstats, color="black")
    for level, color in zip(cval, ("red", "blue", "seagreen")):
        ax.axhline(level, color=color)
    if obj.teststat < cval[2]:
        ax.axvline(obj.bpoint - 1, color="red", linestyle="--")
    ax.set_ylim(min(yvals), max(yvals))
    ax.set_title("Zivot and Andrews Unit Root Test")
    pieces = list(tstats) + list(cval) + [float(min(yvals)), float(max(yvals)), float(n)]
    return PlotUrca(np.asarray(pieces, dtype=float), [figure])


def _plot_residual_acf(res, title="Residuals"):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    res = np.asarray(res, dtype=float)
    pieces = [res, *_acf_pacf_values(res)]
    figure = plt.figure(figsize=(7, 7))
    grid = figure.add_gridspec(2, 2)
    ax = figure.add_subplot(grid[0, :])
    ax.plot(res, color="black")
    ax.axhline(0.0, color="red")
    ax.set_title(title)
    _residual_panels(figure, grid, res, start_row=1)
    figure.tight_layout()
    return PlotUrca(np.concatenate(pieces), [figure])


def _acf_pacf_values(res):
    from scipy.stats import norm

    correlation = _acf(res)
    partial = _pacf(res)
    band = float(norm.ppf(0.975) / math.sqrt(res.size))
    acf_limit = _data_limit(np.concatenate([correlation, [-band, band]]))
    pacf_limit = _data_limit(np.concatenate([partial, [-band, band]]))
    return [correlation, partial, acf_limit, pacf_limit, np.array([band])]


def _residual_panels(figure, grid, res, start_row):
    from scipy.stats import norm

    correlation = _acf(res)
    partial = _pacf(res)
    band = float(norm.ppf(0.975) / math.sqrt(res.size))
    acf_axis = figure.add_subplot(grid[start_row, 0])
    pacf_axis = figure.add_subplot(grid[start_row, 1])
    _stem(acf_axis, np.arange(correlation.size, dtype=float), correlation, _data_limit(np.concatenate([correlation, [-band, band]])), band)
    acf_axis.set_title("Autocorrelations of Residuals")
    _stem(pacf_axis, np.arange(1, partial.size + 1, dtype=float), partial, _data_limit(np.concatenate([partial, [-band, band]])), band)
    pacf_axis.set_title("Partial Autocorrelations of Residuals")
