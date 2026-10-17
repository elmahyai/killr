"""PELT and binary segmentation, from changepoint's C kernels."""

from __future__ import annotations

import math

import numpy as np

PI = math.pi
_TINY = 1e-11


class ChangepointError(Exception):
    pass


def mll_mean(x, x2, x3, n, shape):
    return x2 - (x * x) / n


def mll_var(x, x2, x3, n, shape):
    if x3 <= 0:
        x3 = _TINY
    return n * (math.log(2 * PI) + math.log(x3 / n) + 1)


def mll_meanvar(x, x2, x3, n, shape):
    sigsq = (x2 - ((x * x) / n)) / n
    if sigsq <= 0:
        sigsq = _TINY
    return n * (math.log(2 * PI) + math.log(sigsq) + 1)


def mll_meanvar_exp(x, x2, x3, n, shape):
    return 2 * n * (math.log(x) - math.log(n))


def mll_meanvar_gamma(x, x2, x3, n, shape):
    return 2 * n * shape * (math.log(x) - math.log(n * shape))


def mll_meanvar_poisson(x, x2, x3, n, shape):
    if x == 0:
        return 0.0
    return 2 * x * (math.log(n) - math.log(x))


def mbic_var(x, x2, x3, n, shape):
    return mll_var(x, x2, x3, n, shape) + math.log(n)


def mbic_meanvar(x, x2, x3, n, shape):
    return mll_meanvar(x, x2, x3, n, shape) + math.log(n)


def mbic_mean(x, x2, x3, n, shape):
    return mll_mean(x, x2, x3, n, shape) + math.log(n)


def mbic_meanvar_exp(x, x2, x3, n, shape):
    return mll_meanvar_exp(x, x2, x3, n, shape) + math.log(n)


def mbic_meanvar_gamma(x, x2, x3, n, shape):
    return mll_meanvar_gamma(x, x2, x3, n, shape) + math.log(n)


def mbic_meanvar_poisson(x, x2, x3, n, shape):
    if x == 0:
        return 0.0
    return mll_meanvar_poisson(x, x2, x3, n, shape) + math.log(n)


COSTS = {
    "var.norm": mll_var,
    "mean.norm": mll_mean,
    "meanvar.norm": mll_meanvar,
    "meanvar.exp": mll_meanvar_exp,
    "meanvar.gamma": mll_meanvar_gamma,
    "meanvar.poisson": mll_meanvar_poisson,
    "mean.norm.mbic": mbic_mean,
    "var.norm.mbic": mbic_var,
    "meanvar.norm.mbic": mbic_meanvar,
    "meanvar.exp.mbic": mbic_meanvar_exp,
    "meanvar.gamma.mbic": mbic_meanvar_gamma,
    "meanvar.poisson.mbic": mbic_meanvar_poisson,
    # The exported default string is this name. The C kernel looks up mean.norm.
    "norm.mean": mll_mean,
}


def _min_which(values):
    which = 0
    best = values[0]
    for i in range(1, len(values)):
        if values[i] < best:
            best = values[i]
            which = i
    return best, which


def _max_which(values):
    which = 0
    best = values[0]
    for i in range(1, len(values)):
        if values[i] > best:
            best = values[i]
            which = i
    return best, which


def pelt(sumstat, pen=0.0, cost_func="mean.norm", shape=1.0, minseglen=1):
    """PELT. sumstat has a leading zero row and three columns."""
    stat = np.asarray(sumstat, dtype=float)
    n = stat.shape[0] - 1
    if n < 2:
        raise ChangepointError("Data must have atleast 2 observations to fit a changepoint model.")
    cost = COSTS.get(cost_func)
    if cost is None:
        raise ChangepointError(f"Unknown cost function {cost_func}")
    pen = float(pen)
    shape = float(shape)
    minseglen = int(minseglen)
    like = np.zeros(n + 1)
    last = np.zeros(n + 1, dtype=int)
    count = np.zeros(n + 1, dtype=int)
    like[0] = -pen
    for j in range(minseglen, 2 * minseglen):
        like[j] = cost(stat[j, 0], stat[j, 1], stat[j, 2], j, shape)
        last[j] = 0
        count[j] = 1
    checklist = [0, minseglen]
    for tstar in range(2 * minseglen, n + 1):
        if like[tstar] == 0:
            tmplike = []
            for point in checklist:
                tmplike.append(
                    like[point]
                    + cost(
                        stat[tstar, 0] - stat[point, 0],
                        stat[tstar, 1] - stat[point, 1],
                        stat[tstar, 2] - stat[point, 2],
                        tstar - point,
                        shape,
                    )
                    + pen
                )
            best, which = _min_which(tmplike)
            like[tstar] = best
            last[tstar] = checklist[which]
            count[tstar] = count[last[tstar]] + 1
            checklist = [point for point, value in zip(checklist, tmplike) if value <= like[tstar] + pen]
        checklist.append(tstar - (minseglen - 1))
    found = []
    cursor = n
    while cursor != 0:
        found.append(int(cursor))
        cursor = int(last[cursor])
    cpts = sorted(point for point in found if point > 0)
    return {"lastchangecpts": last, "cpts": np.asarray(cpts, dtype=int), "lastchangelike": like, "ncpts": count}


def binseg(sumstat, pen=0.0, cost_func="mean.norm", shape=1.0, minseglen=2, Q=5):
    stat = np.asarray(sumstat, dtype=float)
    n = stat.shape[0] - 1
    if n < 2:
        raise ChangepointError("Data must have at least 2 observations to fit a changepoint model.")
    Q = int(Q)
    minseglen = int(minseglen)
    if Q > (n / minseglen) + 1:
        raise ChangepointError(f"Q is larger than the maximum number of segments {(n / minseglen) + 1}")
    if Q > n:
        raise ChangepointError("Q is larger than the length of the data length")
    if Q <= 0:
        raise ChangepointError("Q is the maximum number of changepoints so should be greater than 0")
    cost = COSTS.get(cost_func)
    if cost is None:
        raise ChangepointError(f"Unknown cost function {cost_func}")
    pen = float(pen)
    shape = float(shape)
    cptsout = np.zeros(Q, dtype=int)
    likeout = np.zeros(Q)
    oldmax = 1.7e308
    tau = [0, n]
    for q in range(Q):
        lam = np.zeros(n)
        i = 1
        st = tau[0] + 1
        end = tau[1]
        null = (-0.5) * cost(
            stat[end, 0] - stat[st - 1, 0],
            stat[end, 1] - stat[st - 1, 1],
            stat[end, 2] - stat[st - 1, 2],
            end - st + 1,
            shape,
        )
        for j in range(2, n - 2):
            if j == end:
                st = end + 1
                i += 1
                end = tau[i]
                null = (-0.5) * cost(
                    stat[end, 0] - stat[st - 1, 0],
                    stat[end, 1] - stat[st - 1, 1],
                    stat[end, 2] - stat[st - 1, 2],
                    end - st + 1,
                    shape,
                )
            elif (j - st) >= minseglen and (end - j) >= minseglen:
                left = (-0.5) * cost(
                    stat[j, 0] - stat[st - 1, 0],
                    stat[j, 1] - stat[st - 1, 1],
                    stat[j, 2] - stat[st - 1, 2],
                    j - st + 1,
                    shape,
                )
                right = (-0.5) * cost(
                    stat[end, 0] - stat[j, 0],
                    stat[end, 1] - stat[j, 1],
                    stat[end, 2] - stat[j, 2],
                    end - j,
                    shape,
                )
                lam[j] = left + right - null
        maxout, whichout = _max_which(lam)
        cptsout[q] = whichout
        likeout[q] = oldmax if oldmax <= maxout else maxout
        oldmax = likeout[q]
        tau.append(whichout)
        tau.sort()
    op_cps = 0
    stop = False
    while (not stop) and op_cps < Q:
        if (2 * likeout[op_cps]) >= pen:
            op_cps += 1
        else:
            stop = True
    if op_cps == 0:
        cpts = np.asarray([n], dtype=int)
    else:
        cpts = np.asarray(sorted(int(v) for v in cptsout[:op_cps]) + [n], dtype=int)
    cps = np.vstack([cptsout, 2 * likeout])
    return {"cps": cps, "cpts": cpts, "op_cpts": op_cps, "pen": pen}


def reg_cost(y, x, scale, tol):
    """-2 log likelihood, or RSS, of one regression segment. y is the response."""
    nn = len(y)
    if nn == 0:
        return 0.0
    beta, _residuals, _rank, _sv = np.linalg.lstsq(x, y, rcond=tol)
    rss = float(np.sum((y - x @ beta) ** 2))
    if rss < 0:
        rss = 0.0
    scale = float(scale)
    if scale == 0:
        if rss == 0:
            rss = _TINY
        return nn + nn * math.log(2 * PI * rss) - nn * math.log(nn)
    if scale > 0:
        return nn * math.log(2 * PI * scale) + (rss / scale)
    return rss


def reg_pelt(data, pen, minseglen, shape, tol):
    """PELT for a change in normal regression. data columns are response then regressors."""
    values = np.asarray(data, dtype=float)
    n, m = values.shape
    y = values[:, 0]
    x = values[:, 1:]
    like = np.zeros(n + 1)
    last = np.zeros(n + 1, dtype=int)
    count = np.zeros(n + 1, dtype=int)
    like[0] = -pen
    for j in range(minseglen + 1, 2 * minseglen + 1):
        like[j] = reg_cost(y[:j], x[:j], shape, tol)
        last[j] = 0
        count[j] = 1
    checklist = [0, minseglen + 1]
    for tstar in range(2 * minseglen + 1, n + 1):
        if like[tstar] == 0:
            tmplike = []
            for point in checklist:
                tmplike.append(like[point] + reg_cost(y[point:tstar], x[point:tstar], shape, tol) + pen)
            best, which = _min_which(tmplike)
            like[tstar] = best
            last[tstar] = checklist[which]
            count[tstar] = count[last[tstar]] + 1
            checklist = [point for point, value in zip(checklist, tmplike) if value <= like[tstar] + pen]
        checklist.append(tstar - minseglen)
    found = []
    cursor = n
    while cursor != 0:
        found.append(int(cursor))
        cursor = int(last[cursor])
    cpts = sorted(point for point in found if point > 0)
    return {"lastchangecpts": last, "cpts": np.asarray(cpts, dtype=int), "lastchangelike": like, "ncpts": count}


def reg_amoc(data, pen, minseglen, shape, tol):
    values = np.asarray(data, dtype=float)
    n = values.shape[0]
    y = values[:, 0]
    x = values[:, 1:]
    null = reg_cost(y, x, shape, tol)
    tmplike = []
    for tstar in range(minseglen, n - minseglen + 1):
        tmplike.append(reg_cost(y[:tstar], x[:tstar], shape, tol) + reg_cost(y[tstar:], x[tstar:], shape, tol))
    best, which = _min_which(tmplike)
    tau = which + minseglen
    return {"cpts": np.asarray([tau], dtype=int), "null": null, "alt": best, "pen": pen}
