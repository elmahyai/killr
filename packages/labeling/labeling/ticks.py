"""Numeric axis tick-labeling algorithms from the R labeling package."""

import math
import sys


def _seq(start, stop, step):
    if step == 0:
        return [float(start)]
    n = int(math.floor((stop - start) / step + 1e-12)) + 1
    return [start + i * step for i in range(max(n, 0))]


def _nicenum(x, rounding):
    e = math.floor(math.log10(x))
    f = x / (10.0 ** e)
    if rounding:
        nf = 1 if f < 1.5 else 2 if f < 3 else 5 if f < 7 else 10
    else:
        nf = 1 if f <= 1 else 2 if f <= 2 else 5 if f <= 5 else 10
    return nf * 10.0 ** e


def heckbert(dmin, dmax, m):
    span = _nicenum(dmax - dmin, False)
    step = _nicenum(span / (m - 1), True)
    lo = math.floor(dmin / step) * step
    hi = math.ceil(dmax / step) * step
    return _seq(lo, hi, step)


def _wilkinson_scale(dmin, dmax, k, q, mincoverage, m):
    qs = [10.0] + list(q)
    intervals = k - 1
    granularity = 1.0 - abs(k - m) / m
    delta = (dmax - dmin) / intervals
    dbase = 10.0 ** math.floor(math.log10(delta))
    best = None
    for i, qi in enumerate(qs):
        step = qi * dbase
        lo = math.floor(dmin / step) * step
        hi = lo + intervals * step
        if lo <= dmin and hi >= dmax:
            roundness = 1.0 - (i - (1 if lo <= 0 <= hi else 0)) / len(qs)
            coverage = (dmax - dmin) / (hi - lo)
            if coverage > mincoverage:
                score = granularity + roundness + coverage
                if best is None or score > best[3]:
                    best = (lo, hi, step, score)
    return best


def wilkinson(dmin, dmax, m, Q=(1, 5, 2, 2.5, 3, 4, 1.5, 7, 6, 8, 9),
              mincoverage=0.8, mrange=None):
    if mrange is None:
        mrange = range(max(math.floor(m / 2), 2), math.ceil(6 * m) + 1)
    best = None
    for k in mrange:
        result = _wilkinson_scale(dmin, dmax, k, Q, mincoverage, m)
        if result is not None and (best is None or result[3] > best[3]):
            best = result
    if best is None:
        return None
    return _seq(best[0], best[1], best[2])


def _simplicity(q, Q, j, lo, hi, step):
    eps = sys.float_info.epsilon * 100
    i = list(Q).index(q)
    rem = lo % step
    v = 1 if (rem < eps or step - rem < eps) and lo <= 0 <= hi else 0
    return 1 - i / (len(Q) - 1) - j + v


def _coverage(dmin, dmax, lo, hi):
    span = dmax - dmin
    return 1 - 0.5 * ((dmax - hi) ** 2 + (dmin - lo) ** 2) / (0.1 * span) ** 2


def _density(k, m, dmin, dmax, lo, hi):
    r = (k - 1) / (hi - lo)
    rt = (m - 1) / (max(hi, dmax) - min(dmin, lo))
    return 2 - max(r / rt, rt / r)


def extended(dmin, dmax, m, Q=(1, 5, 2, 2.5, 4, 3), only_loose=False,
             w=(0.25, 0.2, 0.5, 0.05)):
    eps = sys.float_info.epsilon * 100
    if dmin > dmax:
        dmin, dmax = dmax, dmin
    if dmax - dmin < eps or dmax - dmin > math.sqrt(sys.float_info.max):
        return [dmin + i * (dmax - dmin) / (m - 1) for i in range(int(m))]
    best = (None, None, None, -2.0)
    j = 1
    while True:
        for q in Q:
            sm = 2 - list(Q).index(q) / (len(Q) - 1) - j
            if w[0] * sm + w[1] + w[2] + w[3] < best[3]:
                j = math.inf
                break
            k = 2
            while True:
                dm = 2 - (k - 1) / (m - 1) if k >= m else 1
                if w[0] * sm + w[1] + w[2] * dm + w[3] < best[3]:
                    break
                delta = (dmax - dmin) / (k + 1) / j / q
                z = math.ceil(math.log10(delta))
                while True:
                    step = j * q * 10.0 ** z
                    cm = (1 - 0.5 * (((step * (k - 1) - (dmax - dmin)) / 2) ** 2 * 2)
                          / (0.1 * (dmax - dmin)) ** 2
                          if step * (k - 1) > dmax - dmin else 1)
                    if w[0] * sm + w[1] * cm + w[2] * dm + w[3] < best[3]:
                        break
                    min_start = math.floor(dmax / step) * j - (k - 1) * j
                    max_start = math.ceil(dmin / step) * j
                    if min_start <= max_start:
                        for start in range(int(min_start), int(max_start) + 1):
                            lo = start * (step / j)
                            hi = lo + step * (k - 1)
                            score = (w[0] * _simplicity(q, Q, j, lo, hi, step)
                                     + w[1] * _coverage(dmin, dmax, lo, hi)
                                     + w[2] * _density(k, m, dmin, dmax, lo, hi)
                                     + w[3])
                            if score > best[3] and (not only_loose or (lo <= dmin and hi >= dmax)):
                                best = (lo, hi, step, score)
                    z += 1
                k += 1
        j += 1
        if math.isinf(j):
            break
    return _seq(best[0], best[1], best[2])


def nelder(dmin, dmax, m, Q=(1, 1.2, 1.6, 2, 2.5, 3, 4, 5, 6, 8, 10)):
    bias = 1e-4
    intervals = m - 1
    step = (dmax - dmin) / intervals
    s = step
    while s <= 1:
        s *= 10
    while s > 10:
        s /= 10
    unit = next((q for q in Q if s - bias < q), 1)
    step *= unit / s
    span = step * intervals
    j = math.floor(0.5 * (1 + (dmin + dmax - span) / step) - bias)
    lo = step * j
    if dmin > 0 and span >= dmax:
        lo = 0
    hi = lo + span
    if not (dmax > 0 or span < -dmin):
        hi, lo = 0, -span
    return _seq(lo, hi, step)


def rpretty(dmin, dmax, m=6, n=None, min_n=None, shrink_sml=0.75,
            high_u_bias=1.5, u5_bias=None):
    if n is None:
        n = math.floor(m) - 1
    if min_n is None:
        min_n = n // 3
    if u5_bias is None:
        u5_bias = 0.5 + 1.5 * high_u_bias
    h, h5, dx = high_u_bias, u5_bias, dmax - dmin
    if dx == 0 and dmax == 0:
        cell, small = 1, True
    else:
        cell = max(abs(dmin), abs(dmax))
        U = 1 + (1 / (1 + h) if h5 >= 1.5 * h + 0.5 else 1.5 / (1 + h5))
        small = dx < cell * U * max(1, n) * 1e-7 * 3
    if small:
        if cell > 10:
            cell = 9 + cell / 10
        cell *= shrink_sml
        if min_n > 1:
            cell /= min_n
    else:
        cell = dx / n if n > 1 else dx
    cell = max(cell, 20 * 1e-7)
    base = 10 ** math.floor(math.log10(cell))
    unit = base
    if 2 * base - cell < h * (cell - unit):
        unit = 2 * base
        if 5 * base - cell < h5 * (cell - unit):
            unit = 5 * base
            if 10 * base - cell < h * (cell - unit):
                unit = 10 * base
    ns = math.floor(dmin / unit + 1e-7)
    nu = math.ceil(dmax / unit - 1e-7)
    while ns * unit > dmin + 1e-7 * unit:
        ns -= 1
    while nu * unit < dmax - 1e-7 * unit:
        nu += 1
    k = math.floor(0.5 + nu - ns)
    if k < min_n:
        extra = min_n - k
        if ns >= 0:
            nu += extra / 2
            ns -= extra / 2 - extra % 2
        else:
            ns -= extra / 2
            nu += extra / 2 + extra % 2
    return _seq(ns * unit, nu * unit, unit)


def matplotlib(dmin, dmax, m):
    dv = abs(dmax - dmin)
    maxabs = max(abs(dmin), abs(dmax))
    if maxabs == 0 or dv / maxabs < 1e-12:
        scale, offset = 1.0, 0.0
    else:
        mean = 0.5 * (dmin + dmax)
        if abs(mean) / dv < 100:
            offset = 0.0
        else:
            offset = (1 if mean > 0 else -1) * 10 ** math.floor(math.log10(abs(mean)))
        scale = 10 ** math.floor(math.log10(dv / m))
    lo, hi = dmin - offset, dmax - offset
    raw = (hi - lo) / m
    scaled = raw / scale
    best_step = 1.0
    best_min, best_max = lo, hi
    for factor in (1, 2, 5, 10):
        if factor >= scaled:
            best_step = factor * scale
            best_min = best_step * math.floor(lo / best_step)
            best_max = best_min + best_step * m
            if best_max >= hi:
                break
    extra = math.floor((best_max - hi) / best_step)
    return _seq(best_min + offset, best_min + offset + (m - extra) * best_step, best_step)


def gnuplot(dmin, dmax, m):
    ntick = math.floor(m)
    power = 10 ** math.floor(math.log10(dmax - dmin))
    norm = (dmax - dmin) / power
    p = (ntick - 1) / norm
    t = (0.05 if p > 40 else 0.1 if p > 20 else 0.2 if p > 10 else
         0.5 if p > 4 else 1 if p > 2 else 2 if p > 0.5 else math.ceil(norm))
    step = t * power
    return _seq(math.floor(dmin / step) * step, math.ceil(dmax / step) * step, step)


def sparks(dmin, dmax, m):
    fm, ratio, key, kount, r, b = m - 1, 0, 1, 0, dmax - dmin, dmin
    while ratio <= 0.8:
        while key <= 2:
            while r <= 1:
                kount += 1
                r *= 10
            while r > 10:
                kount -= 1
                r /= 10
            b *= 10 ** kount
            if b < 0 and b != math.trunc(b):
                b -= 1
            b = math.trunc(b) / 10 ** kount
            r, kount, key = (dmax - b) / fm, 0, key + 2
        fstep = math.ceil(r)
        if r < 1.5:
            fstep -= 0.5
        fstep /= 10 ** kount
        ratio, kount, key = (dmax - dmin) * (fm * fstep), 1, 2
    c = fstep * math.trunc(b / fstep)
    if c < 0 and c != b:
        c -= fstep
    fmin = c if c + fm * fstep > dmax else b
    return _seq(fmin, fstep * (m - 1), fstep)


def thayer(dmin, dmax, m):
    r, b, kount, kod = dmax - dmin, dmin, 0, 0
    while kod < 2:
        while r <= 1:
            kount += 1
            r *= 10
        while r > 10:
            kount -= 1
            r /= 10
        b *= 10 ** kount
        if b < 0:
            b -= 1
        b = math.trunc(b) / 10 ** kount
        r = dmax - b
        a, kount = r / (m - 1), 0
        while a <= 1:
            kount += 1
            a *= 10
        while a > 10:
            kount -= 1
            a /= 10
        ia = math.trunc(a)
        if ia == 6:
            ia = 7
        if ia == 8:
            ia = 9
        aa = -0.5 if a < 1.5 else 0
        a = (aa + 1 + ia) / 10 ** kount
        if (dmax - dmin) / ((m - 1) * a) > 0.8:
            kod = 2
        else:
            kount, r, b, kod = 1, dmax - dmin, dmin, kod + 1
    iab = math.trunc(b / a)
    if iab < 0:
        iab -= 1
    c = a * iab
    if c + (m - 1) * a >= dmax:
        b = c
    return _seq(b, b + a * (m - 1), a)


def extended_figures(samples=100):
    """Draw the labeling comparison figures used by ``labeling``.

    The R routine draws two figures on the current graphics device and
    returns ``NULL``.  Matplotlib has no direct equivalent of R's current
    device, so this creates the corresponding figures and likewise returns
    ``None``.
    """
    import random

    import matplotlib.pyplot as plt

    a = [random.uniform(-100, 400) for _ in range(samples)]
    b = [random.uniform(-100, 400) for _ in range(samples)]
    low = [min(x, y) for x, y in zip(a, b)]
    high = [max(x, y) for x, y in zip(a, b)]
    tick_count = [random.uniform(2, 10) for _ in range(samples)]

    def generate(labeler, **kwargs):
        return [
            labeler(lo, hi, ticks, **kwargs)
            for lo, hi, ticks in zip(low, high, tick_count)
        ]

    results = [
        generate(heckbert),
        generate(wilkinson, mincoverage=0.8),
        generate(extended, only_loose=True),
        generate(extended),
    ]
    names = ["Heckbert", "Wilkinson", "Extended\n(loose)",
             "Extended\n(flexible)"]

    fig1, axes1 = plt.subplots(4, 2, figsize=(8, 10))
    fig1.subplots_adjust(left=0.12, right=0.98, bottom=0.08, top=0.96,
                         hspace=0.55, wspace=0.35)
    for row, (data, name) in enumerate(zip(results, names)):
        coverage = [
            (max(labels) - min(labels)) / (hi - lo)
            for labels, lo, hi in zip(data, low, high)
        ]
        density = [
            len(labels) / ticks
            for labels, ticks in zip(data, tick_count)
        ]
        axes1[row, 0].hist(coverage, bins=[-0.01 + 0.02 * i for i in range(501)],
                           color="darkgray", edgecolor="none")
        axes1[row, 0].set_ylabel(name)
        axes1[row, 0].set_xlim(0.5, 3.5)
        axes1[row, 0].set_ylim(0, 0.12 * samples)
        axes1[row, 1].hist(density, bins=[-0.01 + 0.02 * i for i in range(501)],
                           color="darkgray", edgecolor="none")
        axes1[row, 1].set_ylabel(name)
        axes1[row, 1].set_xlim(0.5, 3.5)
        axes1[row, 1].set_ylim(0, 0.06 * samples)
    axes1[0, 0].set_title("Density")
    axes1[0, 1].set_title("Density")

    fig2, axes2 = plt.subplots(1, 4, figsize=(10, 3))
    fig2.subplots_adjust(left=0.12, right=0.98, bottom=0.18, top=0.82,
                         wspace=0.65)
    for axis, data, name in zip(axes2, results, names):
        steps = []
        for labels in data:
            if len(labels) > 1:
                step = round((labels[1] - labels[0]), 2)
                if step:
                    steps.append(step / (10 ** math.floor(math.log10(step))))
        axis.hist(steps, bins=10, orientation="horizontal",
                  color="gray", edgecolor="none")
        axis.set_title(name)
        axis.set_xlabel("Frequency")

    return None

