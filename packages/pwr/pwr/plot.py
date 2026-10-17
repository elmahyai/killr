"""plot.power.htest from pwr 1.3-0.

The curve is the same sequence of power calculations R draws. Matplotlib draws
that curve. ggplot2 is suggested, not imported, so it is not translated.
"""

from __future__ import annotations

import math

from pwr._stats import PwrError
from pwr.power import (
    PowerHtest,
    pwr_2p2n_test,
    pwr_2p_test,
    pwr_anova_test,
    pwr_chisq_test,
    pwr_norm_test,
    pwr_p_test,
    pwr_r_test,
    pwr_t2n_test,
    pwr_t_test,
)

_METHODS = (
    "One-sample t test power calculation",
    "Two-sample t test power calculation",
    "Paired t test power calculation",
    "t test power calculation",
    "Difference of proportion power calculation for binomial distribution (arcsine transformation)",
    "difference of proportion power calculation for binomial distribution (arcsine transformation)",
    "Balanced one-way analysis of variance power calculation",
    "Chi squared power calculation",
    "Mean power calculation for normal distribution with known variance",
    "proportion power calculation for binomial distribution (arcsine transformation)",
    "approximate correlation power calculation (arctangh transformation)",
)
_BREAKS = 20


def plot_power_htest(x: PowerHtest, xlab=None, ylab=None, main=None, draw: bool = True):
    """The power curve against sample size. Returns the plotted coordinates."""
    if not isinstance(x, PowerHtest):
        raise PwrError("argument must be of class power.htest")
    if x.method not in _METHODS:
        supported = "; ".join(_METHODS)
        raise PwrError(
            f"the method  {x.method}  is not supported. Supported methods include: {supported}"
        )
    curve = _curve(x)
    curve["text_anchor"] = 1 if x["power"] < 0.5 else 0
    if xlab is not None:
        curve["xlab"] = xlab
    if ylab is not None:
        curve["ylab"] = ylab
    if main is not None:
        curve["title"] = main
    if draw:
        _draw(curve)
    return curve


def _curve(x: PowerHtest) -> dict:
    method = x.method
    if method in (
        "One-sample t test power calculation",
        "Two-sample t test power calculation",
        "Paired t test power calculation",
    ):
        kind = {
            "One-sample t test power calculation": "one.sample",
            "Two-sample t test power calculation": "two.sample",
            "Paired t test power calculation": "paired",
        }[method]
        n = x["n"]
        sizes = _sizes(n)
        power = [
            pwr_t_test(n=size, d=x["d"], sig_level=x["sig.level"], type=kind, alternative=x["alternative"])["power"]
            for size in sizes
        ]
        return _bundle(
            sizes,
            power,
            n,
            method,
            f"tails = {x['alternative']}\neffect size d = {x['d']}\nalpha = {x['sig.level']}",
            f"optimal sample size \nn = {math.ceil(n)}\n{x.note}",
        )
    if method == "t test power calculation":
        n = x["n1"] + x["n2"]
        sizes = _sizes(n)
        share = x["n1"] / n
        power = []
        for size in sizes:
            n1 = math.ceil(size * share)
            n2 = size - n1
            if n1 < 2 or n2 < 2:
                power.append(None)
            else:
                power.append(
                    pwr_t2n_test(n1=n1, n2=n2, d=x["d"], sig_level=x["sig.level"], alternative=x["alternative"])["power"]
                )
        return _bundle(
            sizes,
            power,
            n,
            method,
            f"tails = {x['alternative']}\neffect size d = {x['d']}\nalpha = {x['sig.level']}\nn1/n2 = {round(share, 2)}",
            f"optimal sample size \nn = {x['n1']} + {x['n2']} = {n}",
        )
    if method == "Difference of proportion power calculation for binomial distribution (arcsine transformation)":
        n = x["n"]
        sizes = _sizes(n)
        power = [
            pwr_2p_test(n=size, h=x["h"], sig_level=x["sig.level"], alternative=x["alternative"])["power"]
            for size in sizes
        ]
        return _bundle(
            sizes,
            power,
            n,
            "Difference of proportion power calculation\nfor binomial distribution (arcsine transformation)",
            f"tails = {x['alternative']}\neffect size h = {x['h']}\nalpha = {x['sig.level']}",
            f"optimal sample size \nn = {math.ceil(n)}\n{x.note}",
        )
    if method == "difference of proportion power calculation for binomial distribution (arcsine transformation)":
        n = x["n1"] + x["n2"]
        sizes = _sizes(n)
        share = x["n1"] / n
        power = []
        for size in sizes:
            n1 = math.ceil(size * share)
            n2 = size - n1
            if n1 < 2 or n2 < 2:
                power.append(None)
            else:
                power.append(
                    pwr_2p2n_test(n1=n1, n2=n2, h=x["h"], sig_level=x["sig.level"], alternative=x["alternative"])["power"]
                )
        return _bundle(
            sizes,
            power,
            n,
            "Difference of proportion power calculation\nfor binomial distribution (arcsine transformation)",
            f"tails = {x['alternative']}\neffect size h = {x['h']}\nalpha = {x['sig.level']}\nn1/n2 = {round(share, 2)}",
            f"optimal sample size \nn = {x['n1']} + {x['n2']} = {n}",
        )
    if method == "Balanced one-way analysis of variance power calculation":
        n = x["n"]
        sizes = _sizes(n)
        power = [pwr_anova_test(n=size, k=x["k"], f=x["f"], sig_level=x["sig.level"])["power"] for size in sizes]
        return _bundle(
            sizes,
            power,
            n,
            "Balanced one-way analysis of variance \npower calculation",
            f"groups k = {x['k']}\neffect size f = {x['f']}\nalpha = {x['sig.level']}",
            f"optimal sample size \nn = {math.ceil(n)}\n{x.note}",
        )
    if method == "Chi squared power calculation":
        n = x["N"]
        sizes = _sizes(n)
        power = [pwr_chisq_test(N=size, w=x["w"], sig_level=x["sig.level"], df=x["df"])["power"] for size in sizes]
        return _bundle(
            sizes,
            power,
            n,
            method,
            f"effect size w = {x['w']}\ndf = {x['df']}\nalpha = {x['sig.level']}",
            f"optimal sample size \nN = {math.ceil(n)}\n{x.note}",
            xlab="sample size",
        )
    if method == "Mean power calculation for normal distribution with known variance":
        n = x["n"]
        sizes = _sizes(n)
        power = [
            pwr_norm_test(n=size, d=x["d"], sig_level=x["sig.level"], alternative=x["alternative"])["power"]
            for size in sizes
        ]
        return _bundle(
            sizes,
            power,
            n,
            "Mean power calculation for normal distribution\nwith known variance",
            f"tails = {x['alternative']}\neffect size d = {x['d']}\nalpha = {x['sig.level']}",
            f"optimal sample size \nn = {math.ceil(n)}\n{x.note}",
        )
    if method == "proportion power calculation for binomial distribution (arcsine transformation)":
        n = x["n"]
        sizes = _sizes(n)
        power = [
            pwr_p_test(n=size, h=x["h"], sig_level=x["sig.level"], alternative=x["alternative"])["power"]
            for size in sizes
        ]
        return _bundle(
            sizes,
            power,
            n,
            "proportion power calculation\nfor binomial distribution (arcsine transformation)",
            f"tails = {x['alternative']}\neffect size h = {x['h']}\nalpha = {x['sig.level']}",
            f"optimal sample size \nn = {math.ceil(n)}\n{x.note}",
        )
    n = x["n"]
    sizes = _sizes(n)
    power = [
        pwr_r_test(n=size, r=x["r"], sig_level=x["sig.level"], alternative=x["alternative"])["power"]
        for size in sizes
    ]
    return _bundle(
        sizes,
        power,
        n,
        "approximate correlation power calculation\n(arctangh transformation)",
        f"tails = {x['alternative']}\nr = {x['r']}\nalpha = {x['sig.level']}",
        f"optimal sample size \nn = {math.ceil(n)}",
    )


def _sizes(n: float) -> list[float]:
    upper = max(n * 1.5, n + 30)
    return _seq_by(10.0, upper, (upper - 10.0) / _BREAKS)


def _seq_by(start: float, stop: float, step: float) -> list[float]:
    """seq.int(from, to, by) for a positive step that reaches to."""
    count = int(math.floor((stop - start) / step + 1e-10))
    return [start + step * index for index in range(count + 1)]


def _bundle(sizes, power, n, title, legend, optimal, xlab="sample size") -> dict:
    finite = [value for value in power if value is not None]
    if finite and min(finite) < 0.6:
        legend_anchor = 1
    else:
        legend_anchor = 0
    marked = power[0] if power else 0
    # The anchor uses the solved power, which is x$power, not the first curve point.
    return {
        "sample_sizes": sizes,
        "power": power,
        "n": n,
        "line": math.ceil(n),
        "title": title,
        "xlab": xlab,
        "ylab": "test power = 1 - \u03b2",
        "legend": legend,
        "optimal": optimal,
        "legend_anchor": legend_anchor,
        "marked_power": marked,
    }


def _draw(curve: dict) -> None:
    import matplotlib

    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt

    sizes = curve["sample_sizes"]
    power = curve["power"]
    pairs = [(size, value) for size, value in zip(sizes, power) if value is not None]
    figure, axis = plt.subplots()
    axis.plot([size for size, _ in pairs], [value for _, value in pairs], color="red", linewidth=0.8)
    axis.scatter([size for size, _ in pairs], [value for _, value in pairs], color="black", s=12)
    axis.axvline(curve["line"], color="darkblue", linestyle=":", linewidth=1.2)
    axis.set_ylim(0, 1)
    axis.set_xlabel(curve["xlab"])
    axis.set_ylabel(curve["ylab"])
    axis.set_title(curve["title"])
    axis.yaxis.set_major_formatter(lambda value, _pos: f"{value * 100:.0f}%")
    axis.grid(True)
    figure.tight_layout()
    curve["figure"] = figure
