"""Goldfarb-Idnani quadratic programming, from quadprog 1.5-8."""

import math

import numpy as np


def _ddot(n, x, x0, y, y0):
    total = 0.0
    for i in range(n):
        total += x[x0 + i] * y[y0 + i]
    return total


def _daxpy(n, a, x, x0, y, y0):
    for i in range(n):
        y[y0 + i] += a * x[x0 + i]


def _dscal(n, a, x, x0):
    for i in range(n):
        x[x0 + i] *= a


def _dpofa(a, n):
    """Upper Cholesky factor. Returns False when D is not positive definite."""
    for j in range(1, n + 1):
        s = 0.0
        for k in range(1, j):
            t = a[k, j] - _ddot(k - 1, a[:, k], 1, a[:, j], 1)
            t /= a[k, k]
            a[k, j] = t
            s += t * t
        s = a[j, j] - s
        if s <= 0.0:
            return False
        a[j, j] = math.sqrt(s)
    return True


def _dposl(a, n, b):
    for k in range(1, n + 1):
        t = _ddot(k - 1, a[:, k], 1, b, 1)
        b[k] = (b[k] - t) / a[k, k]
    for kb in range(1, n + 1):
        k = n + 1 - kb
        b[k] = b[k] / a[k, k]
        t = -b[k]
        _daxpy(k - 1, t, a[:, k], 1, b, 1)


def _dpori(a, n):
    for k in range(1, n + 1):
        a[k, k] = 1.0 / a[k, k]
        t = -a[k, k]
        _dscal(k - 1, t, a[:, k], 1)
        for j in range(k + 1, n + 1):
            t = a[k, j]
            a[k, j] = 0.0
            _daxpy(k, t, a[:, k], 1, a[:, j], 1)


def _as_matrix(values):
    array = np.array(values, dtype=float)
    if array.ndim != 2:
        raise ValueError("expected a matrix")
    return array


def _as_vector(values):
    return np.array(values, dtype=float).reshape(-1)


def _qpgen2(dmat, dvec, amat, bvec, meq, factorized):
    n = dvec.shape[0]
    q = bvec.shape[0]
    r = min(n, q)
    length = 2 * n + (r * (r + 5)) // 2 + 2 * q + 1
    work = np.zeros(length + 2)
    iact = np.zeros(q + 1, dtype=int)
    lagr = np.zeros(q + 1)
    sol = np.zeros(n + 1)
    dcopy = np.zeros((n + 1, n + 1))
    dcopy[1:, 1:] = dmat
    dvec_work = np.zeros(n + 1)
    dvec_work[1:] = dvec
    amat_work = np.zeros((n + 1, q + 1))
    amat_work[1:, 1:] = amat
    bcopy = np.zeros(q + 1)
    bcopy[1:] = bvec
    ierr = 0 if not factorized else 1

    vsmall = 1.0e-60
    while True:
        vsmall += vsmall
        tmpa = 1.0 + 0.1 * vsmall
        tmpb = 1.0 + 0.2 * vsmall
        if tmpa > 1.0 and tmpb > 1.0:
            break

    work[1 : n + 1] = dvec_work[1:]
    nact = 0
    iterations = [0, 0]

    if ierr == 0:
        if not _dpofa(dcopy, n):
            raise ValueError("matrix D in quadratic function is not positive definite!")
        _dposl(dcopy, n, dvec_work)
        _dpori(dcopy, n)
    else:
        for j in range(1, n + 1):
            total = 0.0
            for i in range(1, j + 1):
                total += dcopy[i, j] * dvec_work[i]
            sol[j] = total
        for j in range(1, n + 1):
            total = 0.0
            for i in range(j, n + 1):
                total += dcopy[j, i] * sol[i]
            dvec_work[j] = total

    crval = 0.0
    for j in range(1, n + 1):
        sol[j] = dvec_work[j]
        crval += work[j] * sol[j]
        work[j] = 0.0
        for i in range(j + 1, n + 1):
            dcopy[i, j] = 0.0
    crval = -crval / 2.0
    unconstrained = dvec_work[1:].copy()

    iwzv = n
    iwrv = iwzv + n
    iwuv = iwrv + r
    iwrm = iwuv + r + 1
    iwsv = iwrm + (r * (r + 1)) // 2
    iwnbv = iwsv + q
    for i in range(1, q + 1):
        total = 0.0
        for j in range(1, n + 1):
            total += amat_work[j, i] * amat_work[j, i]
        work[iwnbv + i] = math.sqrt(total)

    while True:
        iterations[0] += 1
        for i in range(1, q + 1):
            total = -bcopy[i]
            for j in range(1, n + 1):
                total += amat_work[j, i] * sol[j]
            if abs(total) < vsmall:
                total = 0.0
            if i > meq:
                work[iwsv + i] = total
            else:
                work[iwsv + i] = -abs(total)
                if total > 0.0:
                    amat_work[1:, i] *= -1.0
                    bcopy[i] = -bcopy[i]
        for i in range(1, nact + 1):
            work[iwsv + iact[i]] = 0.0
        nvl = 0
        temp = 0.0
        for i in range(1, q + 1):
            if work[iwsv + i] < temp * work[iwnbv + i]:
                nvl = i
                temp = work[iwsv + i] / work[iwnbv + i]
        if nvl == 0:
            for i in range(1, nact + 1):
                lagr[iact[i]] = work[iwuv + i]
            break

        while True:
            for i in range(1, n + 1):
                total = 0.0
                for j in range(1, n + 1):
                    total += dcopy[j, i] * amat_work[j, nvl]
                work[i] = total
            for i in range(1, n + 1):
                work[iwzv + i] = 0.0
            for j in range(nact + 1, n + 1):
                for i in range(1, n + 1):
                    work[iwzv + i] += dcopy[i, j] * work[j]
            t1inf = True
            it1 = 0
            t1 = 0.0
            for i in range(nact, 0, -1):
                total = work[i]
                loc = iwrm + (i * (i + 3)) // 2
                loc1 = loc - i
                for j in range(i + 1, nact + 1):
                    total -= work[loc] * work[iwrv + j]
                    loc += j
                total /= work[loc1]
                work[iwrv + i] = total
                if iact[i] <= meq or total <= 0.0:
                    continue
                t1inf = False
                it1 = i
            if not t1inf:
                t1 = work[iwuv + it1] / work[iwrv + it1]
                for i in range(1, nact + 1):
                    if iact[i] <= meq or work[iwrv + i] <= 0.0:
                        continue
                    candidate = work[iwuv + i] / work[iwrv + i]
                    if candidate < t1:
                        t1 = candidate
                        it1 = i
            znorm = 0.0
            for i in range(1, n + 1):
                znorm += work[iwzv + i] * work[iwzv + i]
            if abs(znorm) <= vsmall:
                if t1inf:
                    raise ValueError("constraints are inconsistent, no solution!")
                for i in range(1, nact + 1):
                    work[iwuv + i] -= t1 * work[iwrv + i]
                work[iwuv + nact + 1] += t1
                it1, nact, iterations = _drop(it1, nact, iact, work, dcopy, n, iwuv, iwrm, iterations)
                continue
            step_sum = 0.0
            for i in range(1, n + 1):
                step_sum += work[iwzv + i] * amat_work[i, nvl]
            tt = -work[iwsv + nvl] / step_sum
            t2min = True
            if not t1inf and t1 < tt:
                tt = t1
                t2min = False
            for i in range(1, n + 1):
                sol[i] += tt * work[iwzv + i]
            crval += tt * step_sum * (tt / 2.0 + work[iwuv + nact + 1])
            for i in range(1, nact + 1):
                work[iwuv + i] -= tt * work[iwrv + i]
            work[iwuv + nact + 1] += tt
            if t2min:
                nact += 1
                iact[nact] = nvl
                loc = iwrm + ((nact - 1) * nact) // 2 + 1
                for i in range(1, nact):
                    work[loc] = work[i]
                    loc += 1
                if nact == n:
                    work[loc] = work[n]
                else:
                    for i in range(n, nact, -1):
                        if work[i] == 0.0:
                            continue
                        gc = max(abs(work[i - 1]), abs(work[i]))
                        gs = min(abs(work[i - 1]), abs(work[i]))
                        temp = math.copysign(gc * math.sqrt(1 + (gs / gc) * (gs / gc)), work[i - 1])
                        gc = work[i - 1] / temp
                        gs = work[i] / temp
                        if gc == 1.0:
                            continue
                        if gc == 0.0:
                            work[i - 1] = gs * temp
                            for j in range(1, n + 1):
                                dcopy[j, i - 1], dcopy[j, i] = dcopy[j, i], dcopy[j, i - 1]
                        else:
                            work[i - 1] = temp
                            nu = gs / (1.0 + gc)
                            for j in range(1, n + 1):
                                temp = gc * dcopy[j, i - 1] + gs * dcopy[j, i]
                                dcopy[j, i] = nu * (dcopy[j, i - 1] + temp) - dcopy[j, i]
                                dcopy[j, i - 1] = temp
                    work[loc] = work[nact]
                break
            total = -bcopy[nvl]
            for j in range(1, n + 1):
                total += sol[j] * amat_work[j, nvl]
            if nvl > meq:
                work[iwsv + nvl] = total
            else:
                work[iwsv + nvl] = -abs(total)
                if total > 0.0:
                    amat_work[1:, nvl] *= -1.0
                    bcopy[nvl] = -bcopy[nvl]
            it1, nact, iterations = _drop(it1, nact, iact, work, dcopy, n, iwuv, iwrm, iterations)
    return {
        "solution": sol[1:].copy(),
        "value": crval,
        "unconstrained_solution": unconstrained,
        "iterations": iterations,
        "Lagrangian": lagr[1:].copy(),
        "iact": np.array([0]) if nact == 0 else iact[1 : nact + 1].copy(),
    }


def _drop(it1, nact, iact, work, dmat, n, iwuv, iwrm, iterations):
    if it1 != nact:
        while it1 < nact:
            loc = iwrm + (it1 * (it1 + 1)) // 2 + 1
            loc1 = loc + it1
            if work[loc1] != 0.0:
                gc = max(abs(work[loc1 - 1]), abs(work[loc1]))
                gs = min(abs(work[loc1 - 1]), abs(work[loc1]))
                temp = math.copysign(
                    gc * math.sqrt(1 + (gs / gc) * (gs / gc)), work[loc1 - 1]
                )
                gc = work[loc1 - 1] / temp
                gs = work[loc1] / temp
                if gc != 1.0:
                    if gc == 0.0:
                        cursor = loc1
                        for i in range(it1 + 1, nact + 1):
                            work[cursor - 1], work[cursor] = work[cursor], work[cursor - 1]
                            cursor += i
                        for i in range(1, n + 1):
                            dmat[i, it1], dmat[i, it1 + 1] = dmat[i, it1 + 1], dmat[i, it1]
                    else:
                        nu = gs / (1.0 + gc)
                        cursor = loc1
                        for i in range(it1 + 1, nact + 1):
                            temp = gc * work[cursor - 1] + gs * work[cursor]
                            work[cursor] = nu * (work[cursor - 1] + temp) - work[cursor]
                            work[cursor - 1] = temp
                            cursor += i
                        for i in range(1, n + 1):
                            temp = gc * dmat[i, it1] + gs * dmat[i, it1 + 1]
                            dmat[i, it1 + 1] = nu * (dmat[i, it1] + temp) - dmat[i, it1 + 1]
                            dmat[i, it1] = temp
            loc1 = loc - it1
            for _i in range(1, it1 + 1):
                work[loc1] = work[loc]
                loc += 1
                loc1 += 1
            work[iwuv + it1] = work[iwuv + it1 + 1]
            iact[it1] = iact[it1 + 1]
            it1 += 1
    work[iwuv + nact] = work[iwuv + nact + 1]
    work[iwuv + nact + 1] = 0.0
    iact[nact] = 0
    nact -= 1
    iterations[1] += 1
    return it1, nact, iterations


def solve_qp(Dmat, dvec, Amat, bvec=None, meq=0, factorized=False):
    """Minimize -d'x + 1/2 x'Dx subject to A'x >= b."""
    matrix = _as_matrix(Dmat)
    linear = _as_vector(dvec)
    constraints = _as_matrix(Amat)
    n = matrix.shape[0]
    q = constraints.shape[1]
    if bvec is None:
        bounds = np.zeros(q)
    else:
        bounds = _as_vector(bvec)
    if n != matrix.shape[1]:
        raise ValueError("Dmat is not symmetric!")
    if n != linear.shape[0]:
        raise ValueError("Dmat and dvec are incompatible!")
    if n != constraints.shape[0]:
        raise ValueError("Amat and dvec are incompatible!")
    if q != bounds.shape[0]:
        raise ValueError("Amat and bvec are incompatible!")
    if meq > q or meq < 0:
        raise ValueError("Value of meq is invalid!")
    return _qpgen2(matrix, linear, constraints, bounds, int(meq), bool(factorized))


def solve_qp_compact(Dmat, dvec, Amat, Aind, bvec=None, meq=0, factorized=False):
    """The same problem with a packed constraint matrix."""
    matrix = _as_matrix(Dmat)
    linear = _as_vector(dvec)
    packed = _as_matrix(Amat)
    index = np.array(Aind, dtype=int)
    if index.ndim == 1:
        index = index.reshape(-1, 1)
    n = matrix.shape[0]
    q = packed.shape[1]
    if bvec is None:
        bounds = np.zeros(q)
    else:
        bounds = _as_vector(bvec)
    if n != matrix.shape[1]:
        raise ValueError("Dmat is not symmetric!")
    if n != linear.shape[0]:
        raise ValueError("Dmat and dvec are incompatible!")
    if index.shape[0] != packed.shape[0] + 1 or index.shape[1] != q or bounds.shape[0] != q:
        raise ValueError("Amat, Aind and bvec are incompatible!")
    if meq > q or meq < 0:
        raise ValueError("Value of meq is invalid!")
    full = np.zeros((n, q))
    # Aind's first row is the count; later rows are 1-based row numbers.
    for col in range(q):
        count = int(index[0, col])
        if count < 1 or count > n:
            raise ValueError("Aind contains illegal indexes!")
        for slot in range(count):
            if slot + 1 >= index.shape[0]:
                raise ValueError("Aind contains illegal indexes!")
            row = int(index[slot + 1, col])
            if row < 1 or row > n:
                raise ValueError("Aind contains illegal indexes!")
            full[row - 1, col] = packed[slot, col]
    return _qpgen2(matrix, linear, full, bounds, int(meq), bool(factorized))
