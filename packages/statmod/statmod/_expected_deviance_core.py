"""Native expected deviance kernels from statmod 1.5.2 ``expectedDeviance.c``."""

from __future__ import annotations

import math

from statmod._expected_deviance_data import (
    NB_A_1_1,
    NB_A_1_2,
    NB_A_1_3,
    NB_A_2_1,
    NB_A_2_2,
    NB_K_1_1,
    NB_K_1_2,
    NB_K_1_3,
    NB_K_2_1,
    NB_K_2_2,
    POIS_ALPHA_WEIGHTS,
    POIS_KAPPA_WEIGHTS,
)

LOW_BOUND = 1e-32
SWEET_CUTOFF1 = 0.736
SWEET_CUTOFF2 = 4.00
BIG_N = 200


def _dbinom(k: int, n: int, p: float) -> float:
    if p <= 0.0:
        return 1.0 if k == 0 else 0.0
    if p >= 1.0:
        return 1.0 if k == n else 0.0
    return math.exp(
        math.lgamma(n + 1.0)
        - math.lgamma(k + 1.0)
        - math.lgamma(n - k + 1.0)
        + k * math.log(p)
        + (n - k) * math.log1p(-p)
    )


def _dnbinom_mu(x: int, size: float, mu: float) -> float:
    prob = size / (size + mu)
    return math.exp(
        math.lgamma(x + size)
        - math.lgamma(size)
        - math.lgamma(x + 1.0)
        + size * math.log(prob)
        + x * math.log1p(-prob)
    )


def _pois_alpha(mu: float) -> float:
    out = 0.0
    x = 0.0
    logmu = 0.0
    iter_ = 0
    weights = POIS_ALPHA_WEIGHTS
    if mu < LOW_BOUND:
        return out
    if mu < 0.0200:
        x = 2 * mu / 0.02 - 1
        logmu = math.log(mu)
    elif mu < 0.4249:
        x = (2 * mu - 0.4449) / 0.4049
        iter_ = 10
    elif mu < 1.5000:
        x = (2 * mu - 1.9249) / 1.0751
        iter_ = 20
    elif mu < 3.5440:
        x = (2 * mu - 5.0440) / 2.0440
        iter_ = 30
    elif mu < 20.000:
        x = (2 * mu - 23.544) / 16.456
        iter_ = 40
    else:
        return 1.0 - 1.0 / (6.0 * mu) - 1.0 / (2.0 * mu * mu)

    x_cheb = [0.0] * 10
    x_cheb[0] = 1.0
    x_cheb[1] = x
    out = weights[iter_] + weights[iter_ + 1] * x
    for i in range(2, 10):
        x_cheb[i] = 2 * x * x_cheb[i - 1] - x_cheb[i - 2]
        out += weights[iter_ + i] * x_cheb[i]
    if mu < 0.0200:
        out = -out * logmu / ((1 + logmu) * (1 + logmu))
    return out


def _pois_kappa(mu: float) -> float:
    out = 0.0
    x = 0.0
    logmu = 0.0
    iter_ = 0
    weights = POIS_KAPPA_WEIGHTS
    if mu < LOW_BOUND:
        return out
    if mu < 0.0200:
        x = 2 * mu / 0.02 - 1
        logmu = math.log(mu) / (1 + math.log(mu))
    elif mu < 0.4966:
        x = (2 * mu - 0.5166) / 0.4766
        iter_ = 10
    elif mu < 1.5000:
        x = (2 * mu - 1.9966) / 1.0034
        iter_ = 20
    elif mu < 4.2714:
        x = (2 * mu - 5.7714) / 2.7714
        iter_ = 30
    elif mu < 20.000:
        x = (2 * mu - 24.2714) / 15.7286
        iter_ = 40
    else:
        return 1.0 - 1.0 / (2.5 * mu * mu)

    x_cheb = [0.0] * 10
    x_cheb[0] = 1.0
    x_cheb[1] = x
    out = weights[iter_] + weights[iter_ + 1] * x
    for i in range(2, 10):
        x_cheb[i] = 2 * x * x_cheb[i - 1] - x_cheb[i - 2]
        out += weights[iter_ + i] * x_cheb[i]
    if mu < 0.0200:
        out = out * mu * logmu * logmu
    return out


def _mpoisdev_scalar(mu: float) -> tuple[float, float]:
    if mu <= LOW_BOUND:
        return 0.0, 0.0
    amu = _pois_alpha(mu)
    kmu = _pois_kappa(mu)
    return kmu / amu, 2.0 * kmu / (amu * amu)


def _mbinomdev_scalar(prob: float, size: int) -> tuple[float, float]:
    pp = prob
    mm = size
    if 1.0 - pp < pp:
        pp = 1.0 - pp
    mu = pp * mm
    if mu < LOW_BOUND:
        return 0.0, 0.0
    if mm < 2:
        mean = -2.0 * (pp * math.log(pp) + (1.0 - pp) * math.log1p(-pp))
        logpp = math.log((1.0 - pp) / pp)
        var = 4.0 * pp * (1.0 - pp) * logpp * logpp
        return mean, var
    if mm < BIG_N:
        pr = [0.0] * (mm + 1)
        de = [0.0] * (mm + 1)
        pr[0] = _dbinom(0, mm, pp)
        pr[mm] = _dbinom(mm, mm, pp)
        de[0] = 2.0 * mm * math.log(1.0 / (1.0 - pp))
        de[mm] = 2.0 * mm * math.log(1.0 / pp)
        dd = pr[0] * de[0] + pr[mm] * de[mm]
        for k in range(1, mm):
            pr[k] = _dbinom(k, mm, pp)
            de[k] = 2.0 * (
                k * math.log(k / mu) + (mm - k) * math.log((mm - k) / (mm - mu))
            )
            dd += pr[k] * de[k]
        var = pr[0] * (de[0] - dd) ** 2 + pr[mm] * (de[mm] - dd) ** 2
        for j in range(1, mm):
            var += pr[j] * (de[j] - dd) ** 2
        return dd, var
    return _mpoisdev_scalar(mu)


def _anbinomdevc_1(mu: float, phi: float) -> float:
    iter_ = 0
    x = 0.0
    y = phi / 0.368 - 1.0
    out = 0.0
    if mu < LOW_BOUND:
        return out
    if mu > 60.0:
        if mu > 120.0:
            iter_ = 12
        elif mu > 80.0:
            iter_ = 6
        y_cheb = [0.0] * 6
        y_cheb[0] = 1.0
        y_cheb[1] = y
        out = NB_A_1_3[iter_] + NB_A_1_3[iter_ + 1] * y
        for i in range(2, 6):
            y_cheb[i] = 2 * y * y_cheb[i - 1] - y_cheb[i - 2]
            out += NB_A_1_3[iter_ + i] * y_cheb[i]
        out = out * (1.0 - 1.0 / (6.0 * mu) - 1.0 / (2.0 * mu * mu))
    elif mu > 20.0:
        if mu < 25.0:
            x = (2 * mu - 45.0) / 5.0
        elif mu < 30.0:
            x = (2 * mu - 55.0) / 5.0
            iter_ = 7
        elif mu < 40.0:
            x = (mu - 35.0) / 5.0
            iter_ = 14
        else:
            x = (mu - 50.0) / 10.0
            iter_ = 21
        x_cheb = [0.0] * 7
        y_cheb = [0.0] * 7
        x_cheb[0] = 1.0
        x_cheb[1] = x
        y_cheb[0] = 1.0
        y_cheb[1] = y
        w1 = NB_A_1_2[iter_] + NB_A_1_2[iter_ + 1] * y
        w2 = NB_A_1_2[iter_ + 7] + NB_A_1_2[iter_ + 8] * y
        w3 = NB_A_1_2[iter_ + 35] + NB_A_1_2[iter_ + 36] * x
        for i in range(2, 7):
            x_cheb[i] = 2 * x * x_cheb[i - 1] - x_cheb[i - 2]
            y_cheb[i] = 2 * y * y_cheb[i - 1] - y_cheb[i - 2]
            w1 += NB_A_1_2[iter_ + i] * y_cheb[i]
            w2 += NB_A_1_2[iter_ + 7 + i] * y_cheb[i]
            w3 += NB_A_1_2[iter_ + 35 + i] * x_cheb[i]
        out = (w2 + (w1 - w2) * w3) * (1.0 - 1.0 / (6.0 * mu) - 1.0 / (2.0 * mu * mu))
    else:
        if mu < 0.01:
            x = 200.0 * mu - 1.0
        elif mu < 0.33:
            x = (2 * mu - 0.34) / 0.32
            iter_ = 49
        elif mu < 1.77:
            x = (2 * mu - 2.10) / 1.44
            iter_ = 98
        elif mu < 4.00:
            x = (2 * mu - 5.77) / 2.23
            iter_ = 147
        elif mu < 10.0:
            x = (mu - 7.0) / 3.0
            iter_ = 196
        else:
            x = (mu - 15.0) / 5.0
            iter_ = 245
        x_cheb = [0.0] * 7
        y_cheb = [0.0] * 7
        x_cheb[0] = 1.0
        x_cheb[1] = x
        y_cheb[0] = 1.0
        y_cheb[1] = y
        for i in range(2, 7):
            x_cheb[i] = 2 * x * x_cheb[i - 1] - x_cheb[i - 2]
            y_cheb[i] = 2 * y * y_cheb[i - 1] - y_cheb[i - 2]
        for i in range(7):
            for j in range(7):
                out += NB_A_1_1[iter_] * x_cheb[j] * y_cheb[i]
                iter_ += 1
        out = out * _pois_alpha(mu)
    return out


def _knbinomdevc_1(mu: float, phi: float) -> float:
    iter_ = 0
    x = 0.0
    y = phi / 0.368 - 1.0
    out = 0.0
    if mu < LOW_BOUND:
        return out
    if mu > 60.0:
        if mu > 250.0:
            iter_ = 18
        elif mu > 120.0:
            iter_ = 12
        elif mu > 80.0:
            iter_ = 6
        y_cheb = [0.0] * 6
        y_cheb[0] = 1.0
        y_cheb[1] = y
        out = NB_K_1_3[iter_] + NB_K_1_3[iter_ + 1] * y
        for i in range(2, 6):
            y_cheb[i] = 2 * y * y_cheb[i - 1] - y_cheb[i - 2]
            out += NB_K_1_3[iter_ + i] * y_cheb[i]
        out = out * (1.0 - 1.0 / (2.5 * mu * mu))
    elif mu > 20.0:
        if mu < 25.0:
            x = (2 * mu - 45.0) / 5.0
        elif mu < 30.0:
            x = (2 * mu - 55.0) / 5.0
            iter_ = 7
        elif mu < 40.0:
            x = (mu - 35.0) / 5.0
            iter_ = 14
        else:
            x = (mu - 50.0) / 10.0
            iter_ = 21
        x_cheb = [0.0] * 7
        y_cheb = [0.0] * 7
        x_cheb[0] = 1.0
        x_cheb[1] = x
        y_cheb[0] = 1.0
        y_cheb[1] = y
        w1 = NB_K_1_2[iter_] + NB_K_1_2[iter_ + 1] * y
        w2 = NB_K_1_2[iter_ + 7] + NB_K_1_2[iter_ + 8] * y
        w3 = NB_K_1_2[iter_ + 35] + NB_K_1_2[iter_ + 36] * x
        for i in range(2, 7):
            x_cheb[i] = 2 * x * x_cheb[i - 1] - x_cheb[i - 2]
            y_cheb[i] = 2 * y * y_cheb[i - 1] - y_cheb[i - 2]
            w1 += NB_K_1_2[iter_ + i] * y_cheb[i]
            w2 += NB_K_1_2[iter_ + 7 + i] * y_cheb[i]
            w3 += NB_K_1_2[iter_ + 35 + i] * x_cheb[i]
        out = (w2 + (w1 - w2) * w3) * (1.0 - 1.0 / (2.5 * mu * mu))
    else:
        if mu < 0.01:
            x = 200.0 * mu - 1.0
        elif mu < 0.33:
            x = (2 * mu - 0.34) / 0.32
            iter_ = 49
        elif mu < 1.30:
            x = (2 * mu - 1.63) / 0.97
            iter_ = 98
        elif mu < 4.00:
            x = (2 * mu - 5.30) / 2.70
            iter_ = 147
        elif mu < 10.0:
            x = (mu - 7.0) / 3.0
            iter_ = 196
        else:
            x = (mu - 15.0) / 5.0
            iter_ = 245
        x_cheb = [0.0] * 7
        y_cheb = [0.0] * 7
        x_cheb[0] = 1.0
        x_cheb[1] = x
        y_cheb[0] = 1.0
        y_cheb[1] = y
        for i in range(2, 7):
            x_cheb[i] = 2 * x * x_cheb[i - 1] - x_cheb[i - 2]
            y_cheb[i] = 2 * y * y_cheb[i - 1] - y_cheb[i - 2]
        for i in range(7):
            for j in range(7):
                out += NB_K_1_1[iter_] * x_cheb[j] * y_cheb[i]
                iter_ += 1
        out = out * _pois_kappa(mu)
    return out


def _anbinomdevc_2(mu: float, phi: float) -> float:
    iter_ = 0
    x = 0.0
    y = phi / 2.0 - 1.0
    out = 0.0
    if mu < LOW_BOUND:
        return out
    if mu < 50.0:
        if mu < 0.01:
            x = mu / 0.01 - 1.0
        elif mu < 0.43:
            x = (mu - 0.22) / 0.21
            iter_ = 100
        elif mu < 3.62:
            x = (2 * mu - 4.05) / 3.19
            iter_ = 200
        elif mu < 10.0:
            x = (2 * mu - 13.62) / 6.38
            iter_ = 300
        elif mu < 30.0:
            x = mu / 10.0 - 2.0
            iter_ = 400
        else:
            x = mu / 10.0 - 4.0
            iter_ = 500
        x_cheb = [0.0] * 10
        y_cheb = [0.0] * 10
        x_cheb[0] = 1.0
        x_cheb[1] = x
        y_cheb[0] = 1.0
        y_cheb[1] = y
        for i in range(2, 10):
            x_cheb[i] = 2 * x * x_cheb[i - 1] - x_cheb[i - 2]
            y_cheb[i] = 2 * y * y_cheb[i - 1] - y_cheb[i - 2]
        for i in range(10):
            for j in range(10):
                out += NB_A_2_1[iter_] * x_cheb[j] * y_cheb[i]
                iter_ += 1
        if mu < 0.01:
            logmu = math.log(mu)
            out = out * (logmu / ((1 + logmu) * (1 + logmu)))
    elif mu < 5000.0:
        if mu < 100.0:
            x = 200.0 / mu - 3.0
        elif mu < 1000.0:
            x = (2000.0 / mu - 11.0) / 9.0
            iter_ = 10
        else:
            x = 2500.0 / mu - 1.5
            iter_ = 20
        x_cheb = [0.0] * 10
        y_cheb = [0.0] * 10
        x_cheb[0] = 1.0
        x_cheb[1] = x
        y_cheb[0] = 1.0
        y_cheb[1] = y
        w1 = NB_A_2_2[iter_] + NB_A_2_2[iter_ + 1] * y
        w2 = NB_A_2_2[iter_ + 10] + NB_A_2_2[iter_ + 11] * y
        w3 = NB_A_2_2[iter_ + 40] + NB_A_2_2[iter_ + 41] * x
        for i in range(2, 10):
            x_cheb[i] = 2 * x * x_cheb[i - 1] - x_cheb[i - 2]
            y_cheb[i] = 2 * y * y_cheb[i - 1] - y_cheb[i - 2]
            w1 += NB_A_2_2[iter_ + i] * y_cheb[i]
            w2 += NB_A_2_2[iter_ + 10 + i] * y_cheb[i]
            w3 += NB_A_2_2[iter_ + 40 + i] * x_cheb[i]
        out = w1 + (w2 - w1) * w3
    else:
        iter_ = 30
        y_cheb = [0.0] * 10
        y_cheb[0] = 1.0
        y_cheb[1] = y
        out = NB_A_2_2[iter_] + NB_A_2_2[iter_ + 1] * y
        for i in range(2, 10):
            y_cheb[i] = 2 * y * y_cheb[i - 1] - y_cheb[i - 2]
            out += NB_A_2_2[iter_ + i] * y_cheb[i]
    return out


def _knbinomdevc_2(mu: float, phi: float) -> float:
    iter_ = 0
    x = 0.0
    y = phi / 2.0 - 1.0
    out = 0.0
    if mu < LOW_BOUND:
        return out
    if mu < 50.0:
        if mu < 0.01:
            x = mu / 0.01 - 1.0
        elif mu < 0.50:
            x = (2 * mu - 0.51) / 0.49
            iter_ = 100
        elif mu < 3.88:
            x = (2 * mu - 4.38) / 3.38
            iter_ = 200
        elif mu < 10.0:
            x = (2 * mu - 13.88) / 6.12
            iter_ = 300
        elif mu < 30.0:
            x = mu / 10.0 - 2.0
            iter_ = 400
        else:
            x = mu / 10.0 - 4.0
            iter_ = 500
        x_cheb = [0.0] * 10
        y_cheb = [0.0] * 10
        x_cheb[0] = 1.0
        x_cheb[1] = x
        y_cheb[0] = 1.0
        y_cheb[1] = y
        for i in range(2, 10):
            x_cheb[i] = 2 * x * x_cheb[i - 1] - x_cheb[i - 2]
            y_cheb[i] = 2 * y * y_cheb[i - 1] - y_cheb[i - 2]
        for i in range(10):
            for j in range(10):
                out += NB_K_2_1[iter_] * x_cheb[j] * y_cheb[i]
                iter_ += 1
        if mu < 0.01:
            logmu = math.log(mu) / (1.0 + math.log(mu))
            out = out * mu * logmu * logmu
    elif mu < 5000.0:
        if mu < 100.0:
            x = 200.0 / mu - 3.0
        elif mu < 1000.0:
            x = (2000.0 / mu - 11.0) / 9.0
            iter_ = 10
        else:
            x = 2500.0 / mu - 1.5
            iter_ = 20
        x_cheb = [0.0] * 10
        y_cheb = [0.0] * 10
        x_cheb[0] = 1.0
        x_cheb[1] = x
        y_cheb[0] = 1.0
        y_cheb[1] = y
        w1 = NB_K_2_2[iter_] + NB_K_2_2[iter_ + 1] * y
        w2 = NB_K_2_2[iter_ + 10] + NB_K_2_2[iter_ + 11] * y
        w3 = NB_K_2_2[iter_ + 40] + NB_K_2_2[iter_ + 41] * x
        for i in range(2, 10):
            x_cheb[i] = 2 * x * x_cheb[i - 1] - x_cheb[i - 2]
            y_cheb[i] = 2 * y * y_cheb[i - 1] - y_cheb[i - 2]
            w1 += NB_K_2_2[iter_ + i] * y_cheb[i]
            w2 += NB_K_2_2[iter_ + 10 + i] * y_cheb[i]
            w3 += NB_K_2_2[iter_ + 40 + i] * x_cheb[i]
        out = w1 + (w2 - w1) * w3
    else:
        iter_ = 30
        y_cheb = [0.0] * 10
        y_cheb[0] = 1.0
        y_cheb[1] = y
        out = NB_K_2_2[iter_] + NB_K_2_2[iter_ + 1] * y
        for i in range(2, 10):
            y_cheb[i] = 2 * y * y_cheb[i - 1] - y_cheb[i - 2]
            out += NB_K_2_2[iter_ + i] * y_cheb[i]
    return out


def _mnbinomdev_scalar(mu: float, size: float) -> tuple[float, float]:
    phi = 1.0 / size
    if mu < LOW_BOUND:
        return 0.0, 0.0
    if phi < SWEET_CUTOFF1:
        amu = _anbinomdevc_1(mu, phi)
        kmu = _knbinomdevc_1(mu, phi)
        return kmu / amu, 2.0 * kmu / (amu * amu)
    if phi < SWEET_CUTOFF2:
        amu = _anbinomdevc_2(mu, phi)
        kmu = _knbinomdevc_2(mu, phi)
        return kmu / amu, 2.0 * kmu / (amu * amu)
    n = int(mu * mu / size + 10.0)
    pr = [0.0] * n
    de = [0.0] * n
    pr[0] = _dnbinom_mu(0, size, mu)
    de[0] = 2.0 * (-size * math.log(size / (mu + size)))
    dd = pr[0] * de[0]
    for i in range(1, n):
        pr[i] = _dnbinom_mu(i, size, mu)
        de[i] = 2.0 * (
            i * math.log(i / mu) - (i + size) * math.log((i + size) / (mu + size))
        )
        dd += pr[i] * de[i]
    var = 0.0
    for i in range(n):
        var += pr[i] * (de[i] - dd) ** 2
    return dd, var
