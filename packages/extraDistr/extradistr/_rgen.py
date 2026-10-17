"""R 4.5 nmath generators for extraDistr, on boot's Mersenne-Twister.

unif_rand is boot.rng.unif. rgamma(shape, scale) uses scale, not rate.
"""

import math

from extradistr._rng import exp_rand, norm_rand, unif

_INV_SQRT_2PI = 0.398942280401432677939946059934
_LN_SQRT_2PI = 0.918938533204672741780329736406
_FACT = (1.0, 1.0, 2.0, 6.0, 24.0, 120.0, 720.0, 5040.0, 40320.0, 362880.0)
_ONE_7 = 0.1428571428571428571
_ONE_12 = 0.0833333333333333333
_ONE_24 = 0.0416666666666666667
_SQRT32 = 5.656854
_EXP_M1 = 0.36787944117144232159
_DBL_MAX = 1.7976931348623157e308
_EXPMAX = 1024.0 * math.log(2.0)
_INT_MAX = 2147483647
_LOG4_TRUNC = 1.3862944
_HYPER_SCALE = 1e25
_HYPER_CON = 57.5646273248511421
_AFC_AL = (
    0.0,
    0.0,
    0.69314718055994530941723212145817,
    1.79175946922805500081247735838070,
    3.17805383034794561964694160129705,
    4.78749174278204599424770093452324,
    6.57925121201010099506017829290394,
    8.52516136106541430016553103634712,
)

# rpois polynomial a0..a7
_PA0 = -0.5
_PA1 = 0.3333333
_PA2 = -0.2500068
_PA3 = 0.2000118
_PA4 = -0.1661269
_PA5 = 0.1421878
_PA6 = -0.1384794
_PA7 = 0.1250060

# rgamma polynomial a1..a7 and q1..q7
_GA1 = 0.3333333
_GA2 = -0.250003
_GA3 = 0.2000062
_GA4 = -0.1662921
_GA5 = 0.1423657
_GA6 = -0.1367177
_GA7 = 0.1233795
_Q1 = 0.04166669
_Q2 = 0.02083148
_Q3 = 0.00801191
_Q4 = 0.00144121
_Q5 = -7.388e-5
_Q6 = 2.4511e-4
_Q7 = 2.424e-4


def _exp(x):
    try:
        return math.exp(x)
    except OverflowError:
        return math.inf


def _log(x):
    if x > 0.0:
        return math.log(x)
    if x == 0.0:
        return -math.inf
    return math.nan


def _forceint(x):
    """R's nearbyint: ties to even, returned as a float."""
    return float(round(x))


def _pow_di(x, n):
    """R_pow_di: integer power by squaring."""
    if math.isnan(x):
        return x
    power = 1.0
    if n == 0:
        return power
    if not math.isfinite(x):
        try:
            return math.pow(x, float(n))
        except (OverflowError, ValueError):
            return math.nan
    if n < 0:
        n = -n
        x = 1.0 / x
    while True:
        if n & 1:
            power *= x
        n >>= 1
        if n:
            x *= x
        else:
            break
    return power


def _i32(x):
    x = int(x) & 0xFFFFFFFF
    if x >= 0x80000000:
        x -= 0x100000000
    return x


class _Pois:
    l = 0
    m = 0
    b1 = 0.0
    b2 = 0.0
    c = 0.0
    c0 = 0.0
    c1 = 0.0
    c2 = 0.0
    c3 = 0.0
    pp = [0.0] * 36
    p0 = 0.0
    p = 0.0
    q = 0.0
    s = 0.0
    d = 0.0
    omega = 0.0
    big_l = 0.0
    muprev = 0.0
    muprev2 = 0.0


class _Gam:
    aa = 0.0
    aaa = 0.0
    s = 0.0
    s2 = 0.0
    d = 0.0
    q0 = 0.0
    b = 0.0
    si = 0.0
    c = 0.0


class _Bet:
    beta = 0.0
    gamma = 0.0
    delta = 0.0
    k1 = 0.0
    k2 = 0.0
    olda = -1.0
    oldb = -1.0


class _Bin:
    c = 0.0
    fm = 0.0
    npq = 0.0
    p1 = 0.0
    p2 = 0.0
    p3 = 0.0
    p4 = 0.0
    qn = 0.0
    xl = 0.0
    xll = 0.0
    xlr = 0.0
    xm = 0.0
    xr = 0.0
    psave = -1.0
    nsave = -1
    m = 0


class _Hyp:
    ks = -1
    n1s = -1
    n2s = -1
    m = 0
    minjx = 0
    maxjx = 0
    k = 0
    n1 = 0
    n2 = 0
    N = 0.0
    w = 0.0
    a = 0.0
    d = 0.0
    s = 0.0
    xl = 0.0
    xr = 0.0
    kl = 0.0
    kr = 0.0
    lamdl = 0.0
    lamdr = 0.0
    p1 = 0.0
    p2 = 0.0
    p3 = 0.0


def _pois_poly(v):
    return (
        (((((((_PA7 * v + _PA6) * v + _PA5) * v + _PA4) * v + _PA3) * v + _PA2) * v + _PA1) * v + _PA0)
    )


def _gamma_poly(v):
    return (((((((_GA7 * v + _GA6) * v + _GA5) * v + _GA4) * v + _GA3) * v + _GA2) * v + _GA1) * v)


def _gamma_q(q0, t, v, s, s2):
    if abs(v) <= 0.25:
        return q0 + 0.5 * t * t * _gamma_poly(v)
    return q0 - s * t + 0.25 * t * t + (s2 + s2) * _log(1.0 + v)


def rpois(lam):
    mu = lam
    if not math.isfinite(mu) or mu < 0.0:
        return math.nan
    if mu <= 0.0:
        return 0.0

    big_mu = mu >= 10.0
    new_big_mu = False
    if not (big_mu and mu == _Pois.muprev):
        if big_mu:
            new_big_mu = True
            _Pois.muprev = mu
            _Pois.s = math.sqrt(mu)
            _Pois.d = 6.0 * mu * mu
            _Pois.big_l = float(math.floor(mu - 1.1484))
        else:
            if mu != _Pois.muprev:
                _Pois.muprev = mu
                _Pois.m = max(1, int(mu))
                _Pois.l = 0
                _Pois.q = _Pois.p0 = _Pois.p = math.exp(-mu)
            while True:
                u = unif()
                if u <= _Pois.p0:
                    return 0.0
                if _Pois.l != 0:
                    k0 = 1 if u <= 0.458 else min(_Pois.l, _Pois.m)
                    for k in range(k0, _Pois.l + 1):
                        if u <= _Pois.pp[k]:
                            return float(k)
                    if _Pois.l == 35:
                        continue
                _Pois.l += 1
                for k in range(_Pois.l, 36):
                    _Pois.p *= mu / k
                    _Pois.q += _Pois.p
                    _Pois.pp[k] = _Pois.q
                    if u <= _Pois.q:
                        _Pois.l = k
                        return float(k)
                _Pois.l = 35

    g = mu + _Pois.s * norm_rand()
    pois = -1.0
    u = 0.0
    fk = 0.0
    difmuk = 0.0
    expo = 0.0
    if g >= 0.0:
        pois = float(math.floor(g))
        if pois >= _Pois.big_l:
            return pois
        fk = pois
        difmuk = mu - fk
        u = unif()
        if _Pois.d * u >= difmuk * difmuk * difmuk:
            return pois

    if new_big_mu or mu != _Pois.muprev2:
        _Pois.muprev2 = mu
        _Pois.omega = _INV_SQRT_2PI / _Pois.s
        _Pois.b1 = _ONE_24 / mu
        _Pois.b2 = 0.3 * _Pois.b1 * _Pois.b1
        _Pois.c3 = _ONE_7 * _Pois.b1 * _Pois.b2
        _Pois.c2 = _Pois.b2 - 15.0 * _Pois.c3
        _Pois.c1 = _Pois.b1 - 6.0 * _Pois.b2 + 45.0 * _Pois.c3
        _Pois.c0 = 1.0 - _Pois.b1 + 3.0 * _Pois.b2 - 15.0 * _Pois.c3
        _Pois.c = 0.1069 / mu

    entered = g >= 0.0
    kflag = 0 if entered else 1
    while True:
        if not entered:
            expo = exp_rand()
            u = 2.0 * unif() - 1.0
            t = 1.8 + (-abs(expo) if u < 0.0 else abs(expo))
            if t <= -0.6744:
                continue
            pois = float(math.floor(mu + _Pois.s * t))
            fk = pois
            difmuk = mu - fk
            kflag = 1
        else:
            entered = False
        if pois < 10.0:
            px = -mu
            py = math.pow(mu, pois) / _FACT[int(pois)]
        else:
            delta = _ONE_12 / fk
            delta = delta * (1.0 - 4.8 * delta * delta)
            v = difmuk / fk
            if abs(v) <= 0.25:
                px = fk * v * v * _pois_poly(v) - delta
            else:
                px = fk * _log(1.0 + v) - difmuk - delta
            py = _INV_SQRT_2PI / math.sqrt(fk)
        x = (0.5 - difmuk) / _Pois.s
        x *= x
        fx = -0.5 * x
        fy = _Pois.omega * (((_Pois.c3 * x + _Pois.c2) * x + _Pois.c1) * x + _Pois.c0)
        if kflag > 0:
            if _Pois.c * abs(u) <= py * _exp(px + expo) - fy * _exp(fx + expo):
                return pois
        elif fy - u * fy <= py * _exp(px - fx):
            return pois


def rgamma(shape, scale=1.0):
    a = shape
    if math.isnan(a) or math.isnan(scale):
        return math.nan
    if a <= 0.0 or scale <= 0.0:
        if scale == 0.0 or a == 0.0:
            return 0.0
        return math.nan
    if not math.isfinite(a) or not math.isfinite(scale):
        return math.inf

    if a < 1.0:
        e = 1.0 + _EXP_M1 * a
        while True:
            p = e * unif()
            if p >= 1.0:
                x = -_log((e - p) / a)
                if exp_rand() >= (1.0 - a) * _log(x):
                    break
            else:
                x = _exp(_log(p) / a)
                if exp_rand() >= x:
                    break
        return scale * x

    if a != _Gam.aa:
        _Gam.aa = a
        _Gam.s2 = a - 0.5
        _Gam.s = math.sqrt(_Gam.s2)
        _Gam.d = _SQRT32 - _Gam.s * 12.0
    t = norm_rand()
    x = _Gam.s + 0.5 * t
    ret = x * x
    if t >= 0.0:
        return scale * ret
    u = unif()
    if _Gam.d * u <= t * t * t:
        return scale * ret

    if a != _Gam.aaa:
        _Gam.aaa = a
        r = 1.0 / a
        _Gam.q0 = (((((((_Q7 * r + _Q6) * r + _Q5) * r + _Q4) * r + _Q3) * r + _Q2) * r + _Q1) * r)
        if a <= 3.686:
            _Gam.b = 0.463 + _Gam.s + 0.178 * _Gam.s2
            _Gam.si = 1.235
            _Gam.c = 0.195 / _Gam.s - 0.079 + 0.16 * _Gam.s
        elif a <= 13.022:
            _Gam.b = 1.654 + 0.0076 * _Gam.s2
            _Gam.si = 1.68 / _Gam.s + 0.275
            _Gam.c = 0.062 / _Gam.s + 0.024
        else:
            _Gam.b = 1.77
            _Gam.si = 0.75
            _Gam.c = 0.1515 / _Gam.s

    if x > 0.0:
        v = t / (_Gam.s + _Gam.s)
        q = _gamma_q(_Gam.q0, t, v, _Gam.s, _Gam.s2)
        if _log(1.0 - u) <= q:
            return scale * ret

    while True:
        e = exp_rand()
        u = unif()
        u = u + u - 1.0
        if u < 0.0:
            t = _Gam.b - _Gam.si * e
        else:
            t = _Gam.b + _Gam.si * e
        if t >= -0.71874483771719:
            v = t / (_Gam.s + _Gam.s)
            q = _gamma_q(_Gam.q0, t, v, _Gam.s, _Gam.s2)
            if q > 0.0:
                w = math.expm1(q)
                if _Gam.c * abs(u) <= w * _exp(e - 0.5 * t * t):
                    break
    x = _Gam.s + 0.5 * t
    return scale * x * x


def _vw(coef, u1, beta):
    v = beta * _log(u1 / (1.0 - u1))
    if v <= _EXPMAX:
        w = coef * _exp(v)
        if not math.isfinite(w):
            w = _DBL_MAX
    else:
        w = _DBL_MAX
    return v, w


def rbeta(a, b):
    aa = a
    bb = b
    if math.isnan(aa) or math.isnan(bb) or aa < 0.0 or bb < 0.0:
        return math.nan
    if not math.isfinite(aa) and not math.isfinite(bb):
        return 0.5
    if aa == 0.0 and bb == 0.0:
        return 0.0 if unif() < 0.5 else 1.0
    if not math.isfinite(aa) or bb == 0.0:
        return 1.0
    if not math.isfinite(bb) or aa == 0.0:
        return 0.0

    qsame = _Bet.olda == aa and _Bet.oldb == bb
    if not qsame:
        _Bet.olda = aa
        _Bet.oldb = bb
    a = min(aa, bb)
    b = max(aa, bb)
    alpha = a + b

    if a <= 1.0:
        if not qsame:
            _Bet.beta = 1.0 / a
            _Bet.delta = 1.0 + b - a
            _Bet.k1 = _Bet.delta * (0.0138889 + 0.0416667 * a) / (b * _Bet.beta - 0.777778)
            _Bet.k2 = 0.25 + (0.5 + 0.25 / _Bet.delta) * a
        while True:
            u1 = unif()
            u2 = unif()
            if u1 < 0.5:
                y = u1 * u2
                z = u1 * y
                if 0.25 * u2 + z - y >= _Bet.k1:
                    continue
            else:
                z = u1 * u1 * u2
                if z <= 0.25:
                    _v, w = _vw(b, u1, _Bet.beta)
                    break
                if z >= _Bet.k2:
                    continue
            v, w = _vw(b, u1, _Bet.beta)
            if alpha * (_log(alpha / (a + w)) + v) - _LOG4_TRUNC >= _log(z):
                break
        if aa == a:
            return a / (a + w)
        return w / (a + w)

    if not qsame:
        _Bet.beta = math.sqrt((alpha - 2.0) / (2.0 * a * b - alpha))
        _Bet.gamma = a + 1.0 / _Bet.beta
    while True:
        u1 = unif()
        u2 = unif()
        v, w = _vw(a, u1, _Bet.beta)
        z = u1 * u1 * u2
        r = _Bet.gamma * v - _LOG4_TRUNC
        s = a + r - w
        if s + 2.609438 >= 5.0 * z:
            break
        t = _log(z)
        if s > t:
            break
        if not (r + alpha * _log(alpha / (b + w)) < t):
            break
    if aa != a:
        return b / (b + w)
    return w / (b + w)


def _binom_small(g, ratio, finish):
    while True:
        ix = 0
        f = _Bin.qn
        u = unif()
        while True:
            if u < f:
                return finish(ix)
            if ix > 110:
                break
            u -= f
            ix += 1
            f *= (g / ix - ratio)


def rbinom(n, prob):
    nin = n
    pp = prob
    if not math.isfinite(nin):
        return math.nan
    size = _forceint(nin)
    if size != nin:
        return math.nan
    if (not math.isfinite(pp)) or size < 0.0 or pp < 0.0 or pp > 1.0:
        return math.nan
    if size == 0.0 or pp == 0.0:
        return 0.0
    if pp == 1.0:
        return size
    if size >= _INT_MAX:
        return math.nan
    n = int(size)
    p = min(pp, 1.0 - pp)
    q = 1.0 - p
    np = n * p
    ratio = p / q
    g = ratio * (n + 1)

    def finish(ix):
        if _Bin.psave > 0.5:
            ix = n - ix
        return float(ix)

    if pp != _Bin.psave or n != _Bin.nsave:
        _Bin.psave = pp
        _Bin.nsave = n
        if np < 30.0:
            _Bin.qn = _pow_di(q, n)
            return _binom_small(g, ratio, finish)
        ffm = np + p
        _Bin.m = math.trunc(ffm)
        _Bin.fm = float(_Bin.m)
        _Bin.npq = np * q
        _Bin.p1 = math.trunc(2.195 * math.sqrt(_Bin.npq) - 4.6 * q) + 0.5
        _Bin.xm = _Bin.fm + 0.5
        _Bin.xl = _Bin.xm - _Bin.p1
        _Bin.xr = _Bin.xm + _Bin.p1
        _Bin.c = 0.134 + 20.5 / (15.3 + _Bin.fm)
        al = (ffm - _Bin.xl) / (ffm - _Bin.xl * p)
        _Bin.xll = al * (1.0 + 0.5 * al)
        al = (_Bin.xr - ffm) / (_Bin.xr * q)
        _Bin.xlr = al * (1.0 + 0.5 * al)
        _Bin.p2 = _Bin.p1 * (1.0 + _Bin.c + _Bin.c)
        _Bin.p3 = _Bin.p2 + _Bin.c / _Bin.xll
        _Bin.p4 = _Bin.p3 + _Bin.c / _Bin.xlr
    elif np < 30.0:
        return _binom_small(g, ratio, finish)

    while True:
        u = unif() * _Bin.p4
        v = unif()
        if u <= _Bin.p1:
            return finish(math.trunc(_Bin.xm - _Bin.p1 * v + u))
        if u <= _Bin.p2:
            x = _Bin.xl + (u - _Bin.p1) / _Bin.c
            v = v * _Bin.c + 1.0 - abs(_Bin.xm - x) / _Bin.p1
            if v > 1.0 or v <= 0.0:
                continue
            ix = math.trunc(x)
        elif u > _Bin.p3:
            ix = math.trunc(_Bin.xr - _log(v) / _Bin.xlr)
            if ix > n:
                continue
            v = v * (u - _Bin.p3) * _Bin.xlr
        else:
            ix = math.trunc(_Bin.xl + _log(v) / _Bin.xll)
            if ix < 0:
                continue
            v = v * (u - _Bin.p2) * _Bin.xll
        k = abs(ix - _Bin.m)
        if k <= 20 or k >= _Bin.npq / 2.0 - 1.0:
            f = 1.0
            if _Bin.m < ix:
                for i in range(_Bin.m + 1, ix + 1):
                    f *= (g / i - ratio)
            elif _Bin.m != ix:
                for i in range(ix + 1, _Bin.m + 1):
                    f /= (g / i - ratio)
            if v <= f:
                return finish(ix)
        else:
            amaxp = (k / _Bin.npq) * ((k * (k / 3.0 + 0.625) + 0.1666666666666) / _Bin.npq + 0.5)
            ynorm = _i32(-k * k) / (2.0 * _Bin.npq)
            alv = _log(v)
            if alv < ynorm - amaxp:
                return finish(ix)
            if alv <= ynorm + amaxp:
                x1 = ix + 1.0
                f1 = _Bin.fm + 1.0
                z = n + 1.0 - _Bin.fm
                w = n - ix + 1.0
                if alv <= (
                    _Bin.xm * _log(f1 / x1)
                    + (n - _Bin.m + 0.5) * _log(z / w)
                    + (ix - _Bin.m) * _log(w * p / (x1 * q))
                    + (13860.0 - (462.0 - (132.0 - (99.0 - 140.0 / (f1 * f1)) / (f1 * f1)) / (f1 * f1)) / (f1 * f1)) / f1 / 166320.0
                    + (13860.0 - (462.0 - (132.0 - (99.0 - 140.0 / (z * z)) / (z * z)) / (z * z)) / (z * z)) / z / 166320.0
                    + (13860.0 - (462.0 - (132.0 - (99.0 - 140.0 / (x1 * x1)) / (x1 * x1)) / (x1 * x1)) / (x1 * x1)) / x1 / 166320.0
                    + (13860.0 - (462.0 - (132.0 - (99.0 - 140.0 / (w * w)) / (w * w)) / (w * w)) / (w * w)) / w / 166320.0
                ):
                    return finish(ix)


def _afc(i):
    if i < 0:
        return -1.0
    if i <= 7:
        return _AFC_AL[i]
    di = float(i)
    i2 = di * di
    return (di + 0.5) * math.log(di) - di + _LN_SQRT_2PI + (0.0833333333333333 - 0.00277777777777778 / i2) / di


def _hyper_finish(ix, kk, nn1, nn2):
    if float(kk) + kk >= _Hyp.N:
        if nn1 > nn2:
            ix = kk - nn2 + ix
        else:
            ix = nn1 - ix
    elif nn1 > nn2:
        ix = kk - ix
    return float(ix)


def _hyper_accept(ix, v):
    m = _Hyp.m
    n1 = _Hyp.n1
    n2 = _Hyp.n2
    k = _Hyp.k
    if m < 100 or ix <= 50:
        f = 1.0
        if m < ix:
            for i in range(m + 1, ix + 1):
                f = f * (n1 - i + 1) * (k - i + 1) / (n2 - k + i) / i
        elif m > ix:
            for i in range(ix + 1, m + 1):
                f = f * i * (n2 - k + i) / (n1 - i + 1) / (k - i + 1)
        return v <= f

    y = float(ix)
    y1 = y + 1.0
    ym = y - m
    yn = n1 - y + 1.0
    yk = k - y + 1.0
    nk = n2 - k + y1
    r = -ym / y1
    sv = ym / yn
    t = ym / yk
    e = -ym / nk
    g = yn * yk / (y1 * nk) - 1.0
    dg = 1.0 if g >= 0.0 else 1.0 + g
    gu = g * (1.0 + g * (-0.5 + g / 3.0))
    gl = gu - 0.25 * (g * g * g * g) / dg
    xm = m + 0.5
    xn = n1 - m + 0.5
    xk = k - m + 0.5
    nm = n2 - k + xm
    ub = (
        y * gu
        - m * gl
        + 0.0034
        + xm * r * (1.0 + r * (-0.5 + r / 3.0))
        + xn * sv * (1.0 + sv * (-0.5 + sv / 3.0))
        + xk * t * (1.0 + t * (-0.5 + t / 3.0))
        + nm * e * (1.0 + e * (-0.5 + e / 3.0))
    )
    alv = _log(v)
    if alv > ub:
        return False
    dr = xm * (r * r * r * r)
    if r < 0.0:
        dr /= 1.0 + r
    ds = xn * (sv * sv * sv * sv)
    if sv < 0.0:
        ds /= 1.0 + sv
    dt = xk * (t * t * t * t)
    if t < 0.0:
        dt /= 1.0 + t
    de = nm * (e * e * e * e)
    if e < 0.0:
        de /= 1.0 + e
    if alv < ub - 0.25 * (dr + ds + dt + de) + (y + m) * (gl - gu) - 0.0078:
        return True
    return alv <= (_Hyp.a - _afc(ix) - _afc(n1 - ix) - _afc(k - ix) - _afc(n2 - k + ix))


def _hyper_one(nn1in, nn2in, kkin):
    if not math.isfinite(nn1in) or not math.isfinite(nn2in) or not math.isfinite(kkin):
        return math.nan
    nn1in = _forceint(nn1in)
    nn2in = _forceint(nn2in)
    kkin = _forceint(kkin)
    if nn1in < 0.0 or nn2in < 0.0 or kkin < 0.0 or kkin > nn1in + nn2in:
        return math.nan
    if nn1in >= _INT_MAX or nn2in >= _INT_MAX or kkin >= _INT_MAX:
        if kkin == 1.0:
            return rbinom(kkin, nn1in / (nn1in + nn2in))
        return math.nan
    nn1 = int(nn1in)
    nn2 = int(nn2in)
    kk = int(kkin)

    if nn1 != _Hyp.n1s or nn2 != _Hyp.n2s:
        setup1 = True
        setup2 = True
    elif kk != _Hyp.ks:
        setup1 = False
        setup2 = True
    else:
        setup1 = False
        setup2 = False
    if setup1:
        _Hyp.n1s = nn1
        _Hyp.n2s = nn2
        _Hyp.N = nn1 + float(nn2)
        if nn1 <= nn2:
            _Hyp.n1 = nn1
            _Hyp.n2 = nn2
        else:
            _Hyp.n1 = nn2
            _Hyp.n2 = nn1
    if setup2:
        _Hyp.ks = kk
        if float(kk) + kk >= _Hyp.N:
            _Hyp.k = math.trunc(_Hyp.N - kk)
        else:
            _Hyp.k = kk
    if setup1 or setup2:
        _Hyp.m = math.trunc((_Hyp.k + 1.0) * (_Hyp.n1 + 1.0) / (_Hyp.N + 2.0))
        _Hyp.minjx = max(0, _Hyp.k - _Hyp.n2)
        _Hyp.maxjx = min(_Hyp.n1, _Hyp.k)

    if _Hyp.minjx == _Hyp.maxjx:
        return _hyper_finish(_Hyp.maxjx, kk, nn1, nn2)

    if _Hyp.m - _Hyp.minjx < 10:
        if setup1 or setup2:
            if _Hyp.k < _Hyp.n2:
                lw = (
                    _afc(_Hyp.n2)
                    + _afc(_Hyp.n1 + _Hyp.n2 - _Hyp.k)
                    - _afc(_Hyp.n2 - _Hyp.k)
                    - _afc(_Hyp.n1 + _Hyp.n2)
                )
            else:
                lw = _afc(_Hyp.n1) + _afc(_Hyp.k) - _afc(_Hyp.k - _Hyp.n2) - _afc(_Hyp.n1 + _Hyp.n2)
            _Hyp.w = _exp(lw + _HYPER_CON)
        while True:
            p = _Hyp.w
            ix = _Hyp.minjx
            u = unif() * _HYPER_SCALE
            restart = False
            while u > p:
                u -= p
                p *= (float(_Hyp.n1) - ix) * (_Hyp.k - ix)
                ix += 1
                p = p / ix / (_Hyp.n2 - _Hyp.k + ix)
                if ix > _Hyp.maxjx:
                    restart = True
                    break
            if not restart:
                return _hyper_finish(ix, kk, nn1, nn2)

    if setup1 or setup2:
        n1 = _Hyp.n1
        n2 = _Hyp.n2
        k = _Hyp.k
        N = _Hyp.N
        m = _Hyp.m
        s = math.sqrt((N - k) * k * n1 * n2 / (N - 1.0) / N / N)
        _Hyp.s = s
        d = math.trunc(1.5 * s) + 0.5
        _Hyp.d = d
        xl = m - d + 0.5
        xr = m + d + 0.5
        _Hyp.xl = xl
        _Hyp.xr = xr
        a = _afc(m) + _afc(n1 - m) + _afc(k - m) + _afc(n2 - k + m)
        _Hyp.a = a
        _Hyp.kl = _exp(
            a
            - _afc(math.trunc(xl))
            - _afc(math.trunc(n1 - xl))
            - _afc(math.trunc(k - xl))
            - _afc(math.trunc(n2 - k + xl))
        )
        _Hyp.kr = _exp(
            a
            - _afc(math.trunc(xr - 1.0))
            - _afc(math.trunc(n1 - xr + 1.0))
            - _afc(math.trunc(k - xr + 1.0))
            - _afc(math.trunc(n2 - k + xr - 1.0))
        )
        _Hyp.lamdl = -_log(xl * (n2 - k + xl) / (n1 - xl + 1.0) / (k - xl + 1.0))
        _Hyp.lamdr = -_log((n1 - xr + 1.0) * (k - xr + 1.0) / xr / (n2 - k + xr))
        _Hyp.p1 = d + d
        _Hyp.p2 = _Hyp.p1 + _Hyp.kl / _Hyp.lamdl
        _Hyp.p3 = _Hyp.p2 + _Hyp.kr / _Hyp.lamdr

    n_uv = 0
    while True:
        u = unif() * _Hyp.p3
        v = unif()
        n_uv += 1
        if n_uv >= 10000:
            return math.nan
        if u < _Hyp.p1:
            ix = math.trunc(_Hyp.xl + u)
        elif u <= _Hyp.p2:
            ix = math.trunc(_Hyp.xl + _log(v) / _Hyp.lamdl)
            if ix < _Hyp.minjx:
                continue
            v = v * (u - _Hyp.p1) * _Hyp.lamdl
        else:
            ix = math.trunc(_Hyp.xr - _log(v) / _Hyp.lamdr)
            if ix > _Hyp.maxjx:
                continue
            v = v * (u - _Hyp.p2) * _Hyp.lamdr
        if _hyper_accept(ix, v):
            return _hyper_finish(ix, kk, nn1, nn2)


def rhyper(nn, m, n, k):
    """R ``rhyper(nn, m, n, k)``: ``nn`` white-ball counts.

    ``m`` white balls, ``n`` black balls, ``k`` drawn.
    """
    if not math.isfinite(nn) or nn < 0.0 or nn >= _INT_MAX:
        return [math.nan]
    return [_hyper_one(m, n, k) for _ in range(math.trunc(nn))]


def rgeom(p):
    if not math.isfinite(p) or p <= 0 or p > 1:
        return math.nan
    return rpois(exp_rand() * ((1.0 - p) / p))


def rnbinom(size, prob):
    if not math.isfinite(prob) or size <= 0 or prob <= 0 or prob > 1:
        return math.nan
    if prob == 1:
        return 0.0
    return rpois(rgamma(size, (1.0 - prob) / prob))


def rcauchy(location=0.0, scale=1.0):
    if math.isnan(location) or not math.isfinite(scale) or scale < 0:
        return math.nan
    if scale == 0 or not math.isfinite(location):
        return location
    return location + scale * math.tan(math.pi * unif())


def rchisq(df):
    return rgamma(df / 2.0, 2.0)


def rt(df):
    if math.isnan(df) or df <= 0:
        return math.nan
    if not math.isfinite(df):
        return norm_rand()
    num = norm_rand()
    return num / math.sqrt(rchisq(df) / df)
