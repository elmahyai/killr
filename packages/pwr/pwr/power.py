"""Power calculations from pwr 1.3-0."""

from __future__ import annotations

import math

from pwr._stats import (
    PwrError,
    match_arg,
    pchisq,
    pf,
    pnorm,
    pt,
    qchisq,
    qf,
    qnorm,
    qt,
    uniroot,
)

_ALTERNATIVE = ("two.sided", "less", "greater")


class PowerHtest(dict):
    """The list R returns with class power.htest. Fields keep R's order."""

    def __init__(self, method: str, note: str | None = None, **fields) -> None:
        super().__init__(fields)
        self.method = method
        self.note = note

    def __getattr__(self, name: str):
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(name) from error

    def __repr__(self) -> str:
        return render(self)


def render(result: PowerHtest, digits: int = 7) -> str:
    """The layout of stats:::print.power.htest."""
    lines = ["", f"     {result.method} ", ""]
    for name, value in result.items():
        shown = value if isinstance(value, str) else _format_number(value, digits)
        lines.append(f"{name:>15} = {shown}")
    lines.append("")
    if result.note is not None:
        lines.append(f"NOTE: {result.note}")
        lines.append("")
    return "\n".join(lines) + "\n"


def cohen_ES(test=("p", "t", "r", "anov", "chisq", "f2"), size=("small", "medium", "large")):
    """Conventional effect sizes from Cohen (1982)."""
    test = match_arg(test, ("p", "t", "r", "anov", "chisq", "f2"), "test")
    size = match_arg(size, ("small", "medium", "large"), "size")
    table = {
        "p": {"small": 0.2, "medium": 0.5, "large": 0.8},
        "t": {"small": 0.2, "medium": 0.5, "large": 0.8},
        "r": {"small": 0.1, "medium": 0.3, "large": 0.5},
        "anov": {"small": 0.1, "medium": 0.25, "large": 0.4},
        "chisq": {"small": 0.1, "medium": 0.3, "large": 0.5},
        "f2": {"small": 0.02, "medium": 0.15, "large": 0.35},
    }
    return PowerHtest(
        "Conventional effect size from Cohen (1982)",
        test=test,
        size=size,
        **{"effect.size": table[test][size]},
    )


def ES_h(p1: float, p2: float) -> float:
    """Cohen's h for two proportions."""
    return 2.0 * math.asin(math.sqrt(p1)) - 2.0 * math.asin(math.sqrt(p2))


def ES_w1(P0, P1) -> float:
    """Cohen's w for a one-way probability vector."""
    total = 0.0
    for left, right in zip(P0, P1, strict=True):
        total += (right - left) ** 2 / left
    return math.sqrt(total)


def ES_w2(P) -> float:
    """Cohen's w for a two-way probability matrix. Rows are the first margin."""
    rows = [list(row) for row in P]
    nrow = len(rows)
    ncol = len(rows[0])
    pi = [sum(row) for row in rows]
    pj = [sum(rows[i][j] for i in range(nrow)) for j in range(ncol)]
    total = 0.0
    for i in range(nrow):
        for j in range(ncol):
            expected = pi[i] * pj[j]
            total += (rows[i][j] - expected) ** 2 / expected
    return math.sqrt(total)


def pwr_t_test(n=None, d=None, sig_level=0.05, power=None, type=("two.sample", "one.sample", "paired"), alternative=_ALTERNATIVE):
    """Power of a one-sample, two-sample, or paired t test."""
    _one_missing([n, d, power, sig_level], "exactly one of n, d, power, and sig.level must be NULL")
    if isinstance(d, str):
        d = cohen_ES(test="t", size=d)["effect.size"]
    _check_unit(sig_level, "sig.level")
    _check_unit(power, "power")
    type = match_arg(type, ("two.sample", "one.sample", "paired"), "type")
    alternative = match_arg(alternative, _ALTERNATIVE, "alternative")
    tsample = {"one.sample": 1, "two.sample": 2, "paired": 1}[type]
    ttside = {"less": 1, "two.sided": 2, "greater": 3}[alternative]
    tside = {"less": 1, "two.sided": 2, "greater": 1}[alternative]
    if tside == 2 and d is not None:
        d = abs(d)

    def body(n, d, sig_level):
        nu = (n - 1) * tsample
        ncp = math.sqrt(n / tsample) * d
        if ttside == 1:
            return pt(qt(sig_level / tside, nu, lower_tail=True), nu, ncp=ncp, lower_tail=True)
        critical = qt(sig_level / tside, nu, lower_tail=False)
        upper = pt(critical, nu, ncp=ncp, lower_tail=False)
        if ttside == 2:
            return upper + pt(-critical, nu, ncp=ncp, lower_tail=True)
        return upper

    if power is None:
        power = body(n, d, sig_level)
    elif d is None:
        interval = {2: (1e-7, 10.0), 1: (-10.0, 5.0), 3: (-5.0, 10.0)}[ttside]
        d = uniroot(lambda d: body(n, d, sig_level) - power, *interval)
    elif n is None:
        n = uniroot(lambda n: body(n, d, sig_level) - power, 2 + 1e-10, 1e9)
    elif sig_level is None:
        sig_level = uniroot(lambda sig_level: body(n, d, sig_level) - power, 1e-10, 1 - 1e-10)
    else:
        raise PwrError("internal error")
    note = {"paired": "n is number of *pairs*", "two.sample": "n is number in *each* group"}.get(type)
    method = {"one.sample": "One-sample", "two.sample": "Two-sample", "paired": "Paired"}[type]
    return PowerHtest(
        f"{method} t test power calculation",
        note,
        n=n,
        d=d,
        **{"sig.level": sig_level, "power": power, "alternative": alternative},
    )


def pwr_t2n_test(n1=None, n2=None, d=None, sig_level=0.05, power=None, alternative=_ALTERNATIVE):
    """Power of a two-sample t test with unequal group sizes."""
    _one_missing([n1, n2, d, power, sig_level], "exactly one of n1, n2, d, power, and sig.level must be NULL")
    if isinstance(d, str):
        d = cohen_ES(test="t", size=d)["effect.size"]
    _check_unit(sig_level, "sig.level")
    _check_unit(power, "power")
    if n1 is not None and n1 < 2:
        raise PwrError("number of observations in the first group must be at least 2")
    if n2 is not None and n2 < 2:
        raise PwrError("number of observations in the second group must be at least 2")
    alternative = match_arg(alternative, _ALTERNATIVE, "alternative")
    ttside = {"less": 1, "two.sided": 2, "greater": 3}[alternative]
    tside = {"less": 1, "two.sided": 2, "greater": 1}[alternative]
    if tside == 2 and d is not None:
        d = abs(d)

    def body(n1, n2, d, sig_level):
        nu = n1 + n2 - 2
        ncp = d * (1.0 / math.sqrt(1.0 / n1 + 1.0 / n2))
        if ttside == 1:
            return pt(qt(sig_level / tside, nu, lower_tail=True), nu, ncp=ncp, lower_tail=True)
        critical = qt(sig_level / tside, nu, lower_tail=False)
        upper = pt(critical, nu, ncp=ncp, lower_tail=False)
        if ttside == 2:
            return upper + pt(-critical, nu, ncp=ncp, lower_tail=True)
        return upper

    if power is None:
        power = body(n1, n2, d, sig_level)
    elif n1 is None:
        n1 = uniroot(lambda n1: body(n1, n2, d, sig_level) - power, 2 + 1e-10, 1e9)
    elif n2 is None:
        n2 = uniroot(lambda n2: body(n1, n2, d, sig_level) - power, 2 + 1e-10, 1e9)
    elif d is None:
        interval = {2: (1e-7, 10.0), 1: (-10.0, 5.0), 3: (-5.0, 10.0)}[ttside]
        d = uniroot(lambda d: body(n1, n2, d, sig_level) - power, *interval)
    elif sig_level is None:
        sig_level = uniroot(lambda sig_level: body(n1, n2, d, sig_level) - power, 1e-10, 1 - 1e-10)
    else:
        raise PwrError("internal error")
    return PowerHtest(
        "t test power calculation",
        n1=n1,
        n2=n2,
        d=d,
        **{"sig.level": sig_level, "power": power, "alternative": alternative},
    )


def pwr_p_test(h=None, n=None, sig_level=0.05, power=None, alternative=_ALTERNATIVE):
    """Power for one proportion, using the arcsine transformation."""
    _one_missing([h, n, power, sig_level], "exactly one of h, n, power, and sig.level must be NULL")
    if isinstance(h, str):
        h = cohen_ES(test="p", size=h)["effect.size"]
    if n is not None and n < 1:
        raise PwrError("number of observations in each group must be at least 1")
    _check_unit(sig_level, "sig.level")
    _check_unit(power, "power")
    alternative = match_arg(alternative, ("two.sided", "less", "greater"), "alternative")
    tside = {"less": 1, "two.sided": 2, "greater": 3}[alternative]
    if tside == 2 and h is not None:
        h = abs(h)

    def body(h, n, sig_level):
        shift = h * math.sqrt(n)
        if tside == 2:
            return pnorm(qnorm(sig_level / 2, lower_tail=False) - shift, lower_tail=False) + pnorm(
                qnorm(sig_level / 2, lower_tail=True) - shift, lower_tail=True
            )
        if tside == 3:
            return pnorm(qnorm(sig_level, lower_tail=False) - shift, lower_tail=False)
        return pnorm(qnorm(sig_level, lower_tail=True) - shift, lower_tail=True)

    if power is None:
        power = body(h, n, sig_level)
    elif h is None:
        interval = {2: (1e-10, 10.0), 1: (-10.0, 5.0), 3: (-5.0, 10.0)}[tside]
        h = uniroot(lambda h: body(h, n, sig_level) - power, *interval)
    elif n is None:
        n = uniroot(lambda n: body(h, n, sig_level) - power, 2 + 1e-10, 1e9)
    elif sig_level is None:
        sig_level = uniroot(lambda sig_level: body(h, n, sig_level) - power, 1e-10, 1 - 1e-10)
    else:
        raise PwrError("internal error")
    return PowerHtest(
        "proportion power calculation for binomial distribution (arcsine transformation)",
        h=h,
        n=n,
        **{"sig.level": sig_level, "power": power, "alternative": alternative},
    )


def pwr_2p_test(h=None, n=None, sig_level=0.05, power=None, alternative=_ALTERNATIVE):
    """Power for a difference of two proportions with equal sample sizes."""
    _one_missing([h, n, power, sig_level], "exactly one of h, n, power, and sig.level must be NULL")
    if isinstance(h, str):
        h = cohen_ES(test="p", size=h)["effect.size"]
    if n is not None and n < 1:
        raise PwrError("number of observations in each group must be at least 1")
    _check_unit(sig_level, "sig.level")
    _check_unit(power, "power")
    alternative = match_arg(alternative, ("two.sided", "less", "greater"), "alternative")
    tside = {"less": 1, "two.sided": 2, "greater": 3}[alternative]
    if tside == 2 and h is not None:
        h = abs(h)

    def body(h, n, sig_level):
        shift = h * math.sqrt(n / 2.0)
        if tside == 3:
            return pnorm(qnorm(sig_level, lower_tail=False) - shift, lower_tail=False)
        if tside == 2:
            return pnorm(qnorm(sig_level / 2, lower_tail=False) - shift, lower_tail=False) + pnorm(
                qnorm(sig_level / 2, lower_tail=True) - shift, lower_tail=True
            )
        return pnorm(qnorm(sig_level, lower_tail=True) - shift, lower_tail=True)

    if power is None:
        power = body(h, n, sig_level)
    elif h is None:
        interval = {2: (1e-10, 10.0), 1: (-10.0, 5.0), 3: (-5.0, 10.0)}[tside]
        h = uniroot(lambda h: body(h, n, sig_level) - power, *interval)
    elif n is None:
        n = uniroot(lambda n: body(h, n, sig_level) - power, 2 + 1e-10, 1e9)
    elif sig_level is None:
        sig_level = uniroot(lambda sig_level: body(h, n, sig_level) - power, 1e-10, 1 - 1e-10)
    else:
        raise PwrError("internal error")
    return PowerHtest(
        "Difference of proportion power calculation for binomial distribution (arcsine transformation)",
        "same sample sizes",
        h=h,
        n=n,
        **{"sig.level": sig_level, "power": power, "alternative": alternative},
    )


def pwr_2p2n_test(h=None, n1=None, n2=None, sig_level=0.05, power=None, alternative=_ALTERNATIVE):
    """Power for a difference of two proportions with unequal sample sizes."""
    _one_missing([h, n1, n2, power, sig_level], "exactly one of h, n1, n2, power, and sig.level must be NULL")
    if isinstance(h, str):
        h = cohen_ES(test="p", size=h)["effect.size"]
    if n1 is not None and n1 < 2:
        raise PwrError("number of observations in the first group must be at least 2")
    if n2 is not None and n2 < 2:
        raise PwrError("number of observations in the second group must be at least 2")
    _check_unit(sig_level, "sig.level")
    _check_unit(power, "power")
    alternative = match_arg(alternative, ("two.sided", "less", "greater"), "alternative")
    tside = {"less": 1, "two.sided": 2, "greater": 3}[alternative]
    if tside == 2 and h is not None:
        h = abs(h)

    def body(h, n1, n2, sig_level):
        shift = h * math.sqrt((n1 * n2) / (n1 + n2))
        if tside == 3:
            return pnorm(qnorm(sig_level, lower_tail=False) - shift, lower_tail=False)
        if tside == 1:
            return pnorm(qnorm(sig_level, lower_tail=True) - shift, lower_tail=True)
        return pnorm(qnorm(sig_level / 2, lower_tail=False) - shift, lower_tail=False) + pnorm(
            qnorm(sig_level / 2, lower_tail=True) - shift, lower_tail=True
        )

    if power is None:
        power = body(h, n1, n2, sig_level)
    elif h is None:
        interval = {2: (1e-10, 10.0), 1: (-10.0, 5.0), 3: (-5.0, 10.0)}[tside]
        h = uniroot(lambda h: body(h, n1, n2, sig_level) - power, *interval)
    elif n1 is None:
        n1 = uniroot(lambda n1: body(h, n1, n2, sig_level) - power, 2 + 1e-10, 1e9)
    elif n2 is None:
        n2 = uniroot(lambda n2: body(h, n1, n2, sig_level) - power, 2 + 1e-10, 1e9)
    elif sig_level is None:
        sig_level = uniroot(lambda sig_level: body(h, n1, n2, sig_level) - power, 1e-10, 1 - 1e-10)
    else:
        raise PwrError("internal error")
    return PowerHtest(
        "difference of proportion power calculation for binomial distribution (arcsine transformation)",
        "different sample sizes",
        h=h,
        n1=n1,
        n2=n2,
        **{"sig.level": sig_level, "power": power, "alternative": alternative},
    )


def pwr_chisq_test(w=None, N=None, df=None, sig_level=0.05, power=None):
    """Power of a chi-square test. df is not solved for."""
    _one_missing([w, N, df, power, sig_level], "exactly one of w, N, df, power, and sig.level must be NULL")
    if w is not None:
        if isinstance(w, str):
            w = cohen_ES(test="chisq", size=w)["effect.size"]
        if w < 0:
            raise PwrError("w must be positive")
    if N is not None and N < 1:
        raise PwrError("number of observations must be at least 1")
    _check_unit(sig_level, "sig.level")
    _check_unit(power, "power")

    def body(w, N, df, sig_level):
        critical = qchisq(sig_level, df, lower_tail=False)
        return pchisq(critical, df, ncp=N * w * w, lower_tail=False)

    if power is None:
        power = body(w, N, df, sig_level)
    elif w is None:
        w = uniroot(lambda w: body(w, N, df, sig_level) - power, 1e-10, 1e9)
    elif N is None:
        N = uniroot(lambda N: body(w, N, df, sig_level) - power, 1 + 1e-10, 1e9)
    elif sig_level is None:
        sig_level = uniroot(lambda sig_level: body(w, N, df, sig_level) - power, 1e-10, 1 - 1e-10)
    else:
        raise PwrError("internal error")
    return PowerHtest(
        "Chi squared power calculation",
        "N is the number of observations",
        w=w,
        N=N,
        df=df,
        **{"sig.level": sig_level, "power": power},
    )


def pwr_r_test(n=None, r=None, sig_level=0.05, power=None, alternative=_ALTERNATIVE):
    """Approximate power of a correlation test, using the arctanh transformation."""
    _one_missing([n, r, power, sig_level], "exactly one of n, r, power, and sig.level must be NULL")
    if isinstance(r, str):
        r = cohen_ES(test="r", size=r)["effect.size"]
    _check_unit(sig_level, "sig.level")
    _check_unit(power, "power")
    if n is not None and n < 4:
        raise PwrError("number of observations must be at least 4")
    alternative = match_arg(alternative, ("two.sided", "less", "greater"), "alternative")
    tside = {"less": 1, "two.sided": 2, "greater": 3}[alternative]
    if tside == 2 and r is not None:
        r = abs(r)

    def body(n, r, sig_level):
        # A direct power calculation assigns r <- -r in the function frame.
        # A root-finder call assigns that name only inside the callback.
        used = -r if tside == 1 else r
        alpha = sig_level if tside != 2 else sig_level / 2.0
        ttt = qt(alpha, n - 2, lower_tail=False)
        rc = math.sqrt(ttt * ttt / (ttt * ttt + n - 2))
        zr = math.atanh(used) + used / (2.0 * (n - 1))
        zrc = math.atanh(rc)
        scale = math.sqrt(n - 3)
        if tside == 2:
            return pnorm((zr - zrc) * scale) + pnorm((-zr - zrc) * scale)
        return pnorm((zr - zrc) * scale)

    if power is None:
        power = body(n, r, sig_level)
        if tside == 1:
            r = -r
    elif n is None:
        n = uniroot(lambda n: body(n, r, sig_level) - power, 4 + 1e-10, 1e9)
    elif r is None:
        interval = (1e-10, 1 - 1e-10) if tside == 2 else (-1 + 1e-10, 1 - 1e-10)
        r = uniroot(lambda r: body(n, r, sig_level) - power, *interval)
    elif sig_level is None:
        sig_level = uniroot(lambda sig_level: body(n, r, sig_level) - power, 1e-10, 1 - 1e-10)
    else:
        raise PwrError("internal error")
    return PowerHtest(
        "approximate correlation power calculation (arctangh transformation)",
        n=n,
        r=r,
        **{"sig.level": sig_level, "power": power, "alternative": alternative},
    )


def pwr_anova_test(k=None, n=None, f=None, sig_level=0.05, power=None):
    """Power of a balanced one-way ANOVA."""
    _one_missing([k, n, f, power, sig_level], "exactly one of k, n, f, power, and sig.level must be NULL")
    if f is not None:
        if isinstance(f, str):
            f = cohen_ES(test="anov", size=f)["effect.size"]
        if f < 0:
            raise PwrError("f must be positive")
    if k is not None and k < 2:
        raise PwrError("number of groups must be at least 2")
    if n is not None and n < 2:
        raise PwrError("number of observations in each group must be at least 2")
    _check_unit(sig_level, "sig.level")
    _check_unit(power, "power")

    def body(k, n, f, sig_level):
        lam = k * n * f * f
        df1 = k - 1
        df2 = (n - 1) * k
        return pf(qf(sig_level, df1, df2, lower_tail=False), df1, df2, ncp=lam, lower_tail=False)

    if power is None:
        power = body(k, n, f, sig_level)
    elif k is None:
        k = uniroot(lambda k: body(k, n, f, sig_level) - power, 2 + 1e-10, 100)
    elif n is None:
        n = uniroot(lambda n: body(k, n, f, sig_level) - power, 2 + 1e-10, 1e9)
    elif f is None:
        f = uniroot(lambda f: body(k, n, f, sig_level) - power, 1e-7, 1e7)
    elif sig_level is None:
        sig_level = uniroot(lambda sig_level: body(k, n, f, sig_level) - power, 1e-10, 1 - 1e-10)
    else:
        raise PwrError("internal error")
    return PowerHtest(
        "Balanced one-way analysis of variance power calculation",
        "n is number in each group",
        k=k,
        n=n,
        f=f,
        **{"sig.level": sig_level, "power": power},
    )


def pwr_norm_test(d=None, n=None, sig_level=0.05, power=None, alternative=_ALTERNATIVE):
    """Power for a normal mean when the variance is known."""
    _one_missing([d, n, power, sig_level], "exactly one of d, n, power, and sig.level must be NULL")
    if isinstance(d, str):
        d = cohen_ES(test="t", size=d)["effect.size"]
    if n is not None and n < 1:
        raise PwrError("number of observations in each group must be at least 1")
    _check_unit(sig_level, "sig.level")
    _check_unit(power, "power")
    alternative = match_arg(alternative, ("two.sided", "less", "greater"), "alternative")
    tside = {"less": 1, "two.sided": 2, "greater": 3}[alternative]
    if tside == 2 and d is not None:
        d = abs(d)

    def body(d, n, sig_level):
        shift = d * math.sqrt(n)
        if tside == 2:
            return pnorm(qnorm(sig_level / 2, lower_tail=False) - shift, lower_tail=False) + pnorm(
                qnorm(sig_level / 2, lower_tail=True) - shift, lower_tail=True
            )
        if tside == 1:
            return pnorm(qnorm(sig_level, lower_tail=True) - shift, lower_tail=True)
        return pnorm(qnorm(sig_level, lower_tail=False) - shift, lower_tail=False)

    if power is None:
        power = body(d, n, sig_level)
    elif d is None:
        interval = {2: (1e-10, 10.0), 1: (-10.0, 5.0), 3: (-5.0, 10.0)}[tside]
        d = uniroot(lambda d: body(d, n, sig_level) - power, *interval)
    elif n is None:
        n = uniroot(lambda n: body(d, n, sig_level) - power, 1 + 1e-10, 1e9)
    elif sig_level is None:
        sig_level = uniroot(lambda sig_level: body(d, n, sig_level) - power, 1e-10, 1 - 1e-10)
    else:
        raise PwrError("internal error")
    return PowerHtest(
        "Mean power calculation for normal distribution with known variance",
        d=d,
        n=n,
        **{"sig.level": sig_level, "power": power, "alternative": alternative},
    )


def pwr_f2_test(u=None, v=None, f2=None, sig_level=0.05, power=None):
    """Power of a multiple regression test."""
    _one_missing([u, v, f2, power, sig_level], "exactly one of u, v, f2, power, and sig.level must be NULL")
    if f2 is not None:
        if isinstance(f2, str):
            f2 = cohen_ES(test="f2", size=f2)["effect.size"]
        if f2 < 0:
            raise PwrError("f2 must be positive")
    if u is not None and u < 1:
        raise PwrError("degree of freedom u for numerator must be at least 1")
    if v is not None and v < 1:
        raise PwrError("degree of freedom v for denominator must be at least 1")
    _check_unit(sig_level, "sig.level")
    _check_unit(power, "power")

    def body(u, v, f2, sig_level):
        lam = f2 * (u + v + 1)
        return pf(qf(sig_level, u, v, lower_tail=False), u, v, ncp=lam, lower_tail=False)

    if power is None:
        power = body(u, v, f2, sig_level)
    elif u is None:
        u = uniroot(lambda u: body(u, v, f2, sig_level) - power, 1 + 1e-10, 100)
    elif v is None:
        v = uniroot(lambda v: body(u, v, f2, sig_level) - power, 1 + 1e-10, 1e9)
    elif f2 is None:
        f2 = uniroot(lambda f2: body(u, v, f2, sig_level) - power, 1e-7, 1e7)
    elif sig_level is None:
        sig_level = uniroot(lambda sig_level: body(u, v, f2, sig_level) - power, 1e-10, 1 - 1e-10)
    else:
        raise PwrError("internal error")
    return PowerHtest(
        "Multiple regression power calculation",
        u=u,
        v=v,
        f2=f2,
        **{"sig.level": sig_level, "power": power},
    )


def _one_missing(values, message: str) -> None:
    if sum(value is None for value in values) != 1:
        raise PwrError(message)


def _check_unit(value, name: str) -> None:
    """The installed test is (!is.null && !is.numeric) || any(out of range)."""
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PwrError(f"\u2018{name}\u2019 must be numeric in [0, 1]")
    if value < 0 or value > 1:
        raise PwrError(f"\u2018{name}\u2019 must be numeric in [0, 1]")


def _format_number(value, digits: int) -> str:
    text = format(float(value), f".{digits}g")
    if "e" in text or "E" in text:
        return text
    if "." not in text:
        return text
    return text
