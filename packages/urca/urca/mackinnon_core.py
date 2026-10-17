"""MacKinnon unit-root p-value core (Fortran fpval port from urca 1.3-4)."""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import numpy as np

_NPZ = Path(__file__).resolve().parent / "mackinnon_tables.npz"


@lru_cache(maxsize=1)
def _tables() -> dict[str, np.ndarray]:
    data = np.load(_NPZ)
    return {key: data[key] for key in data.files}


def _eval(beta: np.ndarray, nobs: int, model: int, nreg: int) -> float:
    if nobs == 0:
        return float(beta[0])
    onobs = 1.0 / nobs if model in (2, 3) else 1.0 / (nobs - nreg)
    if model == 2:
        return float(beta[0] + beta[1] * onobs + beta[2] * onobs**2)
    if model == 3:
        return float(beta[0] + beta[1] * onobs + beta[2] * onobs**2 + beta[3] * onobs**3)
    if model == 4:
        return float(beta[0] + beta[1] * onobs + beta[2] * onobs**2)
    if model == 5:
        return float(beta[0] + beta[1] * onobs + beta[2] * onobs**2 + beta[3] * onobs**3)
    return float(beta[0])


def _gls(xmat: np.ndarray, yvect: np.ndarray, omega: np.ndarray, nx: int, ivrt: int) -> tuple[np.ndarray, float, float, np.ndarray]:
    nobs = xmat.shape[0]
    design = xmat[:, :nx]
    if ivrt == 0:
        om = np.linalg.inv(omega)
        omega[:, :] = om
    else:
        om = omega
    xomx = design.T @ om @ design
    xomy = design.T @ om @ yvect
    beta = np.linalg.solve(xomx, xomy)
    fits = design @ beta
    resid = yvect - fits
    ssr = float(np.sum(resid**2))
    ssrt = float(resid @ om @ resid)
    xomx_inv = np.linalg.inv(xomx)
    return beta, ssr, ssrt, xomx_inv


def _ddnor(ystar: float) -> float:
    p = np.array(
        [
            -6.58749161529837803157e-04,
            -1.60837851487422766278e-02,
            -1.25781726111229246204e-01,
            -3.60344899949804439429e-01,
            -3.05326634961232344035e-01,
            -1.63153871373020978498e-02,
        ]
    )
    q = np.array([2.33520497626869185443e-03, 6.05183413124413191178e-02, 5.27905102951428412248e-01, 1.87295284992346047209e00, 2.56852019228982242072e00])
    a = np.array(
        [
            1.23033935479799725272e03,
            2.05107837782607146532e03,
            1.71204761263407058314e03,
            8.81952221241769090411e02,
            2.98635138197400131132e02,
            6.61191906371416294775e01,
            8.88314979438837594118e00,
            5.64188496988670089180e-01,
            2.15311535474403846343e-08,
        ]
    )
    b = np.array(
        [
            1.23033935480374942043e03,
            3.43936767414372163696e03,
            4.36261909014324715820e03,
            3.29079923573345962678e03,
            1.62138957456669018874e03,
            5.37181101862009857509e02,
            1.17693950891312499305e02,
            1.57449261107098347253e01,
        ]
    )
    c = np.array([3.209377589138469472562e03, 3.774852376853020208137e02, 1.138641541510501556495e02, 3.161123743870565596947e00, 1.857777061846031526730e-01])
    d = np.array([2.844236833439170622273e03, 1.282616526077372275645e03, 2.440246379344441733056e02, 2.360129095234412093499e01])
    orpi = 0.5641895835477562869483
    root2 = 0.70710678118654752440083

    y = ystar
    if ystar < -16.0:
        y = -16.0
    if ystar > 16.0:
        y = 16.0
    x = -y * root2
    if x == 0.0:
        return 0.5
    isw = 1
    if x < 0.0:
        x = -x
        isw = -1
    if x < 0.477:
        x2 = x * x
        x4 = x2 * x2
        x6 = x4 * x2
        x8 = x4 * x4
        top = c[0] + c[1] * x2 + c[2] * x4 + c[3] * x6 + c[4] * x8
        bot = d[0] + d[1] * x2 + d[2] * x4 + d[3] * x6 + x8
        erf = x * top / bot
        erf *= isw
        erfc = 1.0 - erf
        return erfc * 0.5
    if x <= 4.0:
        x2 = x * x
        x3 = x2 * x
        x4 = x2 * x2
        x5 = x3 * x2
        x6 = x3 * x3
        x7 = x3 * x4
        x8 = x4 * x4
        top = (
            a[0]
            + a[1] * x
            + a[2] * x2
            + a[3] * x3
            + a[4] * x4
            + a[5] * x5
            + a[6] * x6
            + a[7] * x7
            + a[8] * x8
        )
        bot = b[0] + b[1] * x + b[2] * x2 + b[3] * x3 + b[4] * x4 + b[5] * x5 + b[6] * x6 + b[7] * x7 + x8
        erfc = math.exp(-x2) * top / bot
        if isw == -1:
            erfc = 2.0 - erfc
        return erfc * 0.5
    x2 = x * x
    xm2 = 1.0 / x2
    xm4 = xm2 * xm2
    xm6 = xm4 * xm2
    xm8 = xm4 * xm4
    xm10 = xm6 * xm4
    top = p[0] + p[1] * xm2 + p[2] * xm4 + p[3] * xm6 + p[4] * xm8 + p[5] * xm10
    bot = q[0] + q[1] * xm2 + q[2] * xm4 + q[3] * xm6 + q[4] * xm8 + xm10
    crap = orpi + top / (bot * x2)
    erfc = math.exp(-x2) * crap / x
    if isw == -1:
        erfc = 2.0 - erfc
    return erfc * 0.5


def _innorz(prob: float) -> float:
    const = 0.398942280401432678
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    pr = prob
    if prob > 0.5:
        pr = 1.0 - prob
    arg = 1.0 / pr**2
    t = math.sqrt(math.log(arg))
    anorm = t - (c0 + c1 * t + c2 * t**2) / (1.0 + d1 * t + d2 * t**2 + d3 * t**3)
    prob2 = _ddnor(anorm)
    pr2 = 1.0 - prob2
    arg = 1.0 / pr2**2
    t = math.sqrt(math.log(arg))
    anorm2 = t - (c0 + c1 * t + c2 * t**2) / (1.0 + d1 * t + d2 * t**2 + d3 * t**3)
    anorm = anorm + anorm - anorm2
    if prob < 0.5:
        anorm = -anorm
    prob2 = _ddnor(anorm)
    error = prob2 - prob
    dens = const * math.exp(-0.5 * anorm**2)
    return anorm - error / dens


def fcrit(
    probs: np.ndarray,
    cnorm: np.ndarray,
    beta: np.ndarray,
    wght: np.ndarray,
    size: float,
    nobs: int,
    model: int,
    nreg: int,
    precrt: float = 2.0,
    np_: int = 9,
) -> float:
    crits = np.array([_eval(beta[:, i - 1], nobs, model, nreg) for i in range(1, 222)])
    diffm = 1000.0
    imin = 0
    for i in range(1, 222):
        diff = abs(size - probs[i - 1])
        if diff < diffm:
            diffm = diff
            imin = i
            if diffm < 1.0e-6:
                break
    nph = np_ // 2
    nptop = 221 - nph
    if imin > nph and imin < nptop:
        yvect = np.zeros(np_)
        xmat = np.zeros((np_, 4))
        for i in range(1, np_ + 1):
            ic = imin - nph - 1 + i
            row = i - 1
            yvect[row] = crits[ic - 1]
            xmat[row, 0] = 1.0
            xmat[row, 1] = cnorm[ic - 1]
            xmat[row, 2] = xmat[row, 1] * cnorm[ic - 1]
            xmat[row, 3] = xmat[row, 2] * cnorm[ic - 1]
        omega = np.zeros((np_, np_))
        for i in range(1, np_ + 1):
            for j in range(i, np_ + 1):
                ic = imin - nph - 1 + i
                jc = imin - nph - 1 + j
                top = probs[ic - 1] * (1.0 - probs[jc - 1])
                bot = probs[jc - 1] * (1.0 - probs[ic - 1])
                val = wght[ic - 1] * wght[jc - 1] * math.sqrt(top / bot)
                omega[i - 1, j - 1] = val
                omega[j - 1, i - 1] = val
        gamma, _ssr, ssrt, xomx = _gls(xmat, yvect, omega, 4, 0)
        sd4 = math.sqrt((ssrt / (np_ - 4)) * xomx[3, 3])
        ttest = abs(gamma[3]) / sd4 if sd4 else 0.0
        anorm = _innorz(size)
        if ttest > precrt:
            return float(gamma[0] + gamma[1] * anorm + gamma[2] * anorm**2 + gamma[3] * anorm**3)
        gamma, _ssr, ssrt, xomx = _gls(xmat, yvect, omega, 3, 1)
        return float(gamma[0] + gamma[1] * anorm + gamma[2] * anorm**2)

    if imin < np_:
        np1 = imin + nph
        if np1 < 5:
            np1 = 5
        yvect = np.zeros(np1)
        xmat = np.zeros((np1, 4))
        for i in range(1, np1 + 1):
            row = i - 1
            yvect[row] = crits[i - 1]
            xmat[row, 0] = 1.0
            xmat[row, 1] = cnorm[i - 1]
            xmat[row, 2] = xmat[row, 1] * cnorm[i - 1]
            xmat[row, 3] = xmat[row, 2] * cnorm[i - 1]
    else:
        np1 = 222 - imin + nph
        if np1 < 5:
            np1 = 5
        yvect = np.zeros(np1)
        xmat = np.zeros((np1, 4))
        for i in range(1, np1 + 1):
            ic = 222 - i
            row = i - 1
            yvect[row] = crits[ic - 1]
            xmat[row, 0] = 1.0
            xmat[row, 1] = cnorm[ic - 1]
            xmat[row, 2] = xmat[row, 1] * cnorm[ic - 1]
            xmat[row, 3] = xmat[row, 2] * cnorm[ic - 1]
    omega = np.zeros((np1, np1))
    for i in range(1, np1 + 1):
        for j in range(i, np1 + 1):
            if imin < np_:
                top = probs[i - 1] * (1.0 - probs[j - 1])
                bot = probs[j - 1] * (1.0 - probs[i - 1])
                val = wght[i - 1] * wght[j - 1] * math.sqrt(top / bot)
            else:
                val = 0.0
                if i == j:
                    val = 1.0
            omega[i - 1, j - 1] = val
            omega[j - 1, i - 1] = val
    gamma, _ssr, ssrt, xomx = _gls(xmat, yvect, omega, 4, 0)
    sd4 = math.sqrt((ssrt / (np1 - 4)) * xomx[3, 3]) if np1 > 4 else 0.0
    ttest = abs(gamma[3]) / sd4 if sd4 else 0.0
    anorm = _innorz(size)
    if ttest > precrt:
        return float(gamma[0] + gamma[1] * anorm + gamma[2] * anorm**2 + gamma[3] * anorm**3)
    gamma, _ssr, ssrt, xomx = _gls(xmat, yvect, omega, 3, 1)
    return float(gamma[0] + gamma[1] * anorm + gamma[2] * anorm**2)


def fpval(
    beta: np.ndarray,
    cnorm: np.ndarray,
    wght: np.ndarray,
    probs: np.ndarray,
    stat: float,
    nobs: int,
    model: int,
    nreg: int,
    precrt: float = 2.0,
    np_: int = 9,
) -> float:
    crits = np.array([_eval(beta[:, i - 1], nobs, model, nreg) for i in range(1, 222)])
    diffm = 1000.0
    imin = 0
    for i in range(1, 222):
        diff = abs(stat - crits[i - 1])
        if diff < diffm:
            diffm = diff
            imin = i
    nph = np_ // 2
    nptop = 221 - nph
    if imin > nph and imin < nptop:
        yvect = np.zeros(np_)
        xmat = np.zeros((np_, 4))
        for i in range(1, np_ + 1):
            ic = imin - nph - 1 + i
            row = i - 1
            yvect[row] = cnorm[ic - 1]
            xmat[row, 0] = 1.0
            xmat[row, 1] = crits[ic - 1]
            xmat[row, 2] = xmat[row, 1] * crits[ic - 1]
            xmat[row, 3] = xmat[row, 2] * crits[ic - 1]
        omega = np.zeros((np_, np_))
        for i in range(1, np_ + 1):
            for j in range(i, np_ + 1):
                ic = imin - nph - 1 + i
                jc = imin - nph - 1 + j
                top = probs[ic - 1] * (1.0 - probs[jc - 1])
                bot = probs[jc - 1] * (1.0 - probs[ic - 1])
                val = wght[ic - 1] * wght[jc - 1] * math.sqrt(top / bot)
                omega[i - 1, j - 1] = val
                omega[j - 1, i - 1] = val
        gamma, _ssr, ssrt, xomx = _gls(xmat, yvect, omega, 4, 0)
        sd4 = math.sqrt((ssrt / (np_ - 4)) * xomx[3, 3])
        ttest = abs(gamma[3]) / sd4 if sd4 else 0.0
        if ttest > precrt:
            crfit = gamma[0] + gamma[1] * stat + gamma[2] * stat**2 + gamma[3] * stat**3
        else:
            gamma, _ssr, ssrt, xomx = _gls(xmat, yvect, omega, 3, 1)
            crfit = gamma[0] + gamma[1] * stat + gamma[2] * stat**2
        return _ddnor(crfit)

    if imin < np_:
        np1 = imin + nph
        if np1 < 5:
            np1 = 5
        yvect = np.zeros(np1)
        xmat = np.zeros((np1, 4))
        for i in range(1, np1 + 1):
            row = i - 1
            yvect[row] = cnorm[i - 1]
            xmat[row, 0] = 1.0
            xmat[row, 1] = crits[i - 1]
            xmat[row, 2] = xmat[row, 1] * crits[i - 1]
            xmat[row, 3] = xmat[row, 2] * crits[i - 1]
    else:
        np1 = 222 - imin + nph
        if np1 < 5:
            np1 = 5
        yvect = np.zeros(np1)
        xmat = np.zeros((np1, 4))
        for i in range(1, np1 + 1):
            ic = 222 - i
            row = i - 1
            yvect[row] = cnorm[ic - 1]
            xmat[row, 0] = 1.0
            xmat[row, 1] = crits[ic - 1]
            xmat[row, 2] = xmat[row, 1] * crits[ic - 1]
            xmat[row, 3] = xmat[row, 2] * crits[ic - 1]
    omega = np.zeros((np1, np1))
    for i in range(1, np1 + 1):
        for j in range(i, np1 + 1):
            if imin < np_:
                top = probs[i - 1] * (1.0 - probs[j - 1])
                bot = probs[j - 1] * (1.0 - probs[i - 1])
                val = wght[i - 1] * wght[j - 1] * math.sqrt(top / bot)
            else:
                val = 0.0
                if i == j:
                    val = 1.0
            omega[i - 1, j - 1] = val
            omega[j - 1, i - 1] = val
    gamma, _ssr, ssrt, xomx = _gls(xmat, yvect, omega, 4, 0)
    sd4 = math.sqrt((ssrt / (np1 - 4)) * xomx[3, 3]) if np1 > 4 else 0.0
    ttest = abs(gamma[3]) / sd4 if sd4 else 0.0
    if ttest > precrt:
        crfit = gamma[0] + gamma[1] * stat + gamma[2] * stat**2 + gamma[3] * stat**3
    else:
        gamma, _ssr, ssrt, xomx = _gls(xmat, yvect, omega, 3, 1)
        crfit = gamma[0] + gamma[1] * stat + gamma[2] * stat**2
    pval = _ddnor(crfit)
    if imin == 1 and pval > probs[0]:
        pval = probs[0]
    if imin == 221 and pval < probs[220]:
        pval = probs[220]
    return pval


def urcval_p(
    arg: float,
    nobs: int,
    itt: int,
    itv: int,
) -> float:
    tab = _tables()
    key = f"itt{itt}_itv{itv}"
    beta = tab[f"{key}_beta"]
    wght = tab[f"{key}_wght"]
    model = int(tab[f"{key}_model"])
    nreg = int(tab[f"{key}_nreg"])
    probs = tab["probs"]
    cnorm = tab["cnorm"]
    return fpval(beta, cnorm, wght, probs, arg, nobs, model, nreg)


def urcval_q(
    arg: float,
    nobs: int,
    itt: int,
    itv: int,
) -> float:
    if arg < 0.0001 or arg > 0.9999:
        return float("nan")
    tab = _tables()
    key = f"itt{itt}_itv{itv}"
    beta = tab[f"{key}_beta"]
    wght = tab[f"{key}_wght"]
    model = int(tab[f"{key}_model"])
    nreg = int(tab[f"{key}_nreg"])
    probs = tab["probs"]
    cnorm = tab["cnorm"]
    return fcrit(probs, cnorm, beta, wght, arg, nobs, model, nreg)
