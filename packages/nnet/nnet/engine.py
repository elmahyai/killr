"""Feed-forward net, BFGS fit, and Hessian from nnet/src/nnet.c.

The optimiser is vmmin from R's stats, the routine nnet's C code calls.
Weight updates follow that source line for line so the fitted weights
agree with R.
"""

from __future__ import annotations

import math
import sys

import numpy as np

_EPS = 1.0e-80
_STEPREDN = 0.2
_ACCTOL = 0.0001
_RELTEST = 10.0


def _finite(value):
    return math.isfinite(value)


def vmmin(n0, b, fminfn, fmingr, maxit, trace, mask, abstol, reltol, n_report=10):
    """R's BFGS vmmin. ``b`` is updated in place. Returns (Fmin, fail)."""
    if maxit <= 0:
        return fminfn(b), 0
    if n_report <= 0:
        raise ValueError('REPORT must be > 0 (method = "BFGS")')
    free = [i for i in range(n0) if mask[i]]
    n = len(free)
    g = [0.0] * n0
    step = [0.0] * n
    point = [0.0] * n
    change = [0.0] * n
    inverse = [[0.0] * (i + 1) for i in range(n)]
    value = fminfn(b)
    if not _finite(value):
        raise ValueError("initial value in 'vmmin' is not finite")
    if trace:
        sys.stdout.write("initial  value %f \n" % value)
    fmin = value
    gradcount = 1
    fmingr(b, g)
    iteration = 1
    ilast = gradcount
    count = 0
    while True:
        if ilast == gradcount:
            for i in range(n):
                row = inverse[i]
                for j in range(i):
                    row[j] = 0.0
                row[i] = 1.0
        for i in range(n):
            point[i] = b[free[i]]
            change[i] = g[free[i]]
        gradproj = 0.0
        for i in range(n):
            total = 0.0
            row = inverse[i]
            for j in range(i + 1):
                total -= row[j] * g[free[j]]
            for j in range(i + 1, n):
                total -= inverse[j][i] * g[free[j]]
            step[i] = total
            gradproj += total * g[free[i]]
        if gradproj < 0.0:
            steplength = 1.0
            accepted = False
            while True:
                count = 0
                for i in range(n):
                    b[free[i]] = point[i] + steplength * step[i]
                    if (_RELTEST + point[i]) == (_RELTEST + b[free[i]]):
                        count += 1
                if count < n:
                    value = fminfn(b)
                    accepted = _finite(value) and (
                        value <= fmin + gradproj * steplength * _ACCTOL
                    )
                    if not accepted:
                        steplength *= _STEPREDN
                if count == n or accepted:
                    break
            enough = (value > abstol) and abs(value - fmin) > reltol * (abs(fmin) + reltol)
            if not enough:
                count = n
                fmin = value
            if count < n:
                fmin = value
                fmingr(b, g)
                gradcount += 1
                iteration += 1
                curvature = 0.0
                for i in range(n):
                    step[i] = steplength * step[i]
                    change[i] = g[free[i]] - change[i]
                    curvature += step[i] * change[i]
                if curvature > 0.0:
                    quad = 0.0
                    for i in range(n):
                        total = 0.0
                        row = inverse[i]
                        for j in range(i + 1):
                            total += row[j] * change[j]
                        for j in range(i + 1, n):
                            total += inverse[j][i] * change[j]
                        point[i] = total
                        quad += total * change[i]
                    quad = 1.0 + quad / curvature
                    for i in range(n):
                        row = inverse[i]
                        for j in range(i + 1):
                            row[j] += (
                                quad * step[i] * step[j]
                                - point[i] * step[j]
                                - step[i] * point[j]
                            ) / curvature
                else:
                    ilast = gradcount
            elif ilast < gradcount:
                count = 0
                ilast = gradcount
        else:
            count = 0
            if ilast == gradcount:
                count = n
            else:
                ilast = gradcount
        if trace and iteration % n_report == 0:
            sys.stdout.write("iter%4d value %f\n" % (iteration, value))
        if iteration >= maxit:
            break
        if gradcount - ilast > 2 * n:
            ilast = gradcount
        if count == n and ilast == gradcount:
            break
    if trace:
        sys.stdout.write("final  value %f \n" % fmin)
        if iteration < maxit:
            sys.stdout.write("converged\n")
        else:
            sys.stdout.write("stopped after %i iterations\n" % iteration)
    fail = 0 if iteration < maxit else 1
    return fmin, fail


def _sigmoid(total):
    if total < -15.0:
        return 0.0
    if total > 15.0:
        return 1.0
    return 1.0 / (1.0 + math.exp(-total))


def _sigmoid_prime(value):
    return value * (1.0 - value)


def _sigmoid_prime_prime(value):
    return value * (1.0 - value) * (1.0 - 2.0 * value)


class Net:
    """One network, matching the static state in nnet.c."""

    def set_net(self, n, nconn, conn, decay, nsunits, entropy, softmax, censored):
        self.n_inputs = int(n[0])
        self.n_hidden = int(n[1])
        self.n_outputs = int(n[2])
        self.n_units = 1 + self.n_inputs + self.n_hidden + self.n_outputs
        self.nconn = [int(v) for v in nconn]
        self.conn = [int(v) for v in conn]
        self.n_weights = self.nconn[self.n_units]
        self.decay = [float(v) for v in decay]
        self.nsunits = int(nsunits)
        self.entropy = int(entropy)
        self.linout = self.nsunits < self.n_units
        self.softmax = int(softmax)
        self.censored = int(censored)
        self.outputs = [0.0] * self.n_units
        self.outputs[0] = 1.0
        self.error_sums = [0.0] * self.n_units
        self.errors = [0.0] * self.n_units
        self.wts = [0.0] * self.n_weights
        self.slopes = [0.0] * self.n_weights
        self.probs = [0.0] * self.n_units
        self.first_hidden = 1 + self.n_inputs
        self.first_output = 1 + self.n_inputs + self.n_hidden
        self.total_error = 0.0

    def _read_inputs(self, flat, case, nr):
        outputs = self.outputs
        for i in range(self.n_inputs):
            outputs[i + 1] = flat[case + i * nr]

    def fpass(self, flat, case, goal, wx, nr):
        self._read_inputs(flat, case, nr)
        outputs = self.outputs
        wts = self.wts
        conn = self.conn
        nconn = self.nconn
        nsunits = self.nsunits
        for unit in range(self.first_hidden, self.n_units):
            total = 0.0
            for link in range(nconn[unit], nconn[unit + 1]):
                total += outputs[conn[link]] * wts[link]
            if unit < nsunits:
                total = _sigmoid(total)
            outputs[unit] = total
        if self.softmax:
            peak = outputs[self.first_output]
            for unit in range(self.first_output + 1, self.n_units):
                if outputs[unit] > peak:
                    peak = outputs[unit]
            denom = 0.0
            probs = self.probs
            for unit in range(self.first_output, self.n_units):
                probs[unit] = math.exp(outputs[unit] - peak)
                denom += probs[unit]
            this_error = 0.0
            for unit in range(self.first_output, self.n_units):
                probs[unit] = probs[unit] / denom
                target = goal[unit - self.first_output]
                if self.censored:
                    if target == 1:
                        this_error += probs[unit]
                elif target > 0:
                    if probs[unit] > 0:
                        self.total_error -= wx * target * math.log(probs[unit])
                    else:
                        self.total_error += wx * 1000
            if self.censored:
                if this_error > 0:
                    self.total_error -= wx * math.log(this_error)
                else:
                    self.total_error += wx * 1000
            return
        for unit in range(self.first_output, self.n_units):
            self.total_error += wx * self._loss(outputs[unit], goal[unit - self.first_output])

    def _loss(self, predicted, target):
        if self.entropy:
            total = 0.0
            if target > 0:
                total -= target * math.log((predicted + _EPS) / target)
            if target < 1:
                total -= (1 - target) * math.log((1 - predicted + _EPS) / (1 - target))
            return total
        gap = predicted - target
        return gap * gap

    def bpass(self, goal, wx):
        outputs = self.outputs
        error_sums = self.error_sums
        errors = self.errors
        first = self.first_output
        if self.softmax:
            if self.censored:
                denom = 0.0
                for unit in range(first, self.n_units):
                    if goal[unit - first] == 1:
                        denom += self.probs[unit]
                for unit in range(first, self.n_units):
                    error_sums[unit] = self.probs[unit]
                    if goal[unit - first] == 1:
                        error_sums[unit] -= self.probs[unit] / denom
            else:
                total = 0.0
                for unit in range(first, self.n_units):
                    total += goal[unit - first]
                for unit in range(first, self.n_units):
                    error_sums[unit] = total * self.probs[unit] - goal[unit - first]
        elif self.entropy:
            for unit in range(first, self.n_units):
                error_sums[unit] = outputs[unit] - goal[unit - first]
        else:
            for unit in range(first, self.n_units):
                error_sums[unit] = 2 * (outputs[unit] - goal[unit - first])
                if unit < self.nsunits:
                    error_sums[unit] *= _sigmoid_prime(outputs[unit])
        for unit in range(self.first_hidden, first):
            error_sums[unit] = 0.0
        conn = self.conn
        nconn = self.nconn
        wts = self.wts
        slopes = self.slopes
        for unit in range(self.n_units - 1, self.first_hidden - 1, -1):
            errors[unit] = error_sums[unit]
            if unit < first:
                errors[unit] *= _sigmoid_prime(outputs[unit])
            for link in range(nconn[unit], nconn[unit + 1]):
                source = conn[link]
                error_sums[source] += errors[unit] * wts[link]
                slopes[link] += wx * errors[unit] * outputs[source]

    def _goals(self, flat, case, nr):
        start = self.n_inputs
        return [flat[case + (start + j) * nr] for j in range(self.n_outputs)]

    def fminfn(self, p):
        wts = self.wts
        for i in range(self.n_weights):
            wts[i] = p[i]
        self.total_error = 0.0
        flat = self.train
        nr = self.n_train
        weights = self.case_weights
        for case in range(nr):
            self.fpass(flat, case, self._goals(flat, case, nr), weights[case], nr)
        penalty = 0.0
        decay = self.decay
        for i in range(self.n_weights):
            penalty += decay[i] * p[i] * p[i]
        return self.total_error + penalty

    def fmingr(self, p, df):
        wts = self.wts
        slopes = self.slopes
        decay = self.decay
        for i in range(self.n_weights):
            wts[i] = p[i]
        for j in range(self.n_weights):
            slopes[j] = 2 * decay[j] * wts[j]
        self.total_error = 0.0
        flat = self.train
        nr = self.n_train
        weights = self.case_weights
        for case in range(nr):
            goal = self._goals(flat, case, nr)
            wx = weights[case]
            self.fpass(flat, case, goal, wx, nr)
            self.bpass(goal, wx)
        for j in range(self.n_weights):
            df[j] = slopes[j]

    def prepare(self, x, y, weights):
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        self.n_train = x.shape[0]
        self.train = np.concatenate(
            [np.asfortranarray(x).ravel(order="F"), np.asfortranarray(y).ravel(order="F")]
        )
        self.case_weights = [float(v) for v in weights]

    def fit(self, wts, maxit, trace, mask, abstol, reltol):
        value, fail = vmmin(
            self.n_weights,
            wts,
            self.fminfn,
            self.fmingr,
            int(maxit),
            bool(trace),
            mask,
            float(abstol),
            float(reltol),
        )
        return value, fail

    def predict(self, x, wts):
        x = np.asarray(x, dtype=np.float64)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        ntr = x.shape[0]
        flat = np.asfortranarray(x).ravel(order="F")
        for i in range(self.n_weights):
            self.wts[i] = float(wts[i])
        result = np.zeros((ntr, self.n_outputs), dtype=np.float64)
        goal = [0.5] * self.n_outputs
        for case in range(ntr):
            self.fpass(flat, case, goal, 1.0, ntr)
            if self.softmax:
                for i in range(self.n_outputs):
                    result[case, i] = self.probs[self.first_output + i]
            else:
                for i in range(self.n_outputs):
                    result[case, i] = self.outputs[self.first_output + i]
        return result

    def hessian(self, x, y, weights, wts):
        self.prepare(x, y, weights)
        for i in range(self.n_weights):
            self.wts[i] = float(wts[i])
        nw = self.n_weights
        nu = self.n_units
        lower = [[0.0] * (i + 1) for i in range(nw)]
        weight_to = [[0.0] * nu for _ in range(nu)]
        first = self.first_output
        hidden = self.first_hidden
        for unit in range(first, nu):
            for link in range(self.nconn[unit], self.nconn[unit + 1]):
                weight_to[self.conn[link]][unit] = self.wts[link]
        flat = self.train
        nr = self.n_train
        for case in range(nr):
            goal = self._goals(flat, case, nr)
            self._p_hessian(flat, case, goal, self.case_weights[case], nr, lower, weight_to)
        for i in range(nw):
            lower[i][i] += 2 * self.decay[i]
        hess = np.zeros((nw, nw), dtype=np.float64)
        for i in range(nw):
            for j in range(i + 1):
                hess[i, j] = lower[i][j]
                hess[j, i] = lower[i][j]
        return hess

    def _p_hessian(self, flat, case, goal, wx, nr, lower, weight_to):
        self.fpass(flat, case, goal, 1.0, nr)
        self.bpass(goal, 1.0)
        outputs = self.outputs
        errors = self.errors
        probs = self.probs
        conn = self.conn
        nconn = self.nconn
        first = self.first_output
        nu = self.n_units
        if self.softmax:
            h = [0.0] * nu
            h1 = [0.0] * nu
            total_target = 0.0
            share = 0.0
            for source in range(nu):
                sum1 = 0.0
                sum2 = 0.0
                total_target = 0.0
                share = 0.0
                for unit in range(first, nu):
                    sum1 += weight_to[source][unit] * probs[unit]
                    target = goal[unit - first]
                    share += target * probs[unit]
                    sum2 += weight_to[source][unit] * probs[unit] * target
                    total_target += target
                h[source] = sum1
                h1[source] = sum2 / share
            if self.censored:
                total_target = 1
            for to1 in range(nu):
                for j1 in range(nconn[to1], nconn[to1 + 1]):
                    from1 = conn[j1]
                    first1 = to1 < first
                    for to2 in range(nu):
                        for j2 in range(nconn[to2], nconn[to2 + 1]):
                            if j2 > j1:
                                continue
                            from2 = conn[j2]
                            first2 = to2 < first
                            if (not first1) and (not first2):
                                if self.censored:
                                    tmp = -probs[to1] * probs[to2] * (
                                        1
                                        - goal[to1 - first]
                                        * goal[to2 - first]
                                        / share
                                        / share
                                    )
                                    if to1 == to2:
                                        tmp += probs[to1] * (1 - goal[to1 - first] / share)
                                    lower[j1][j2] += wx * (
                                        tmp * outputs[from1] * outputs[from2]
                                    )
                                else:
                                    tmp = -probs[to1] * probs[to2]
                                    if to1 == to2:
                                        tmp += probs[to1]
                                    lower[j1][j2] += wx * total_target * (
                                        tmp * outputs[from1] * outputs[from2]
                                    )
                            elif first1 and first2:
                                sum1 = 0.0
                                sum2 = 0.0
                                for unit in range(first, nu):
                                    sum1 += errors[unit] * weight_to[to1][unit]
                                    tmp = weight_to[to1][unit] * weight_to[to2][unit] * probs[unit]
                                    if self.censored:
                                        tmp *= 1 - goal[unit - first] / share
                                    sum2 += tmp
                                if self.censored:
                                    sum2 += -h[to1] * h[to2] + h1[to1] * h1[to2]
                                    scale = (
                                        _sigmoid_prime(outputs[to1])
                                        * _sigmoid_prime(outputs[to2])
                                        * sum2
                                    )
                                else:
                                    sum2 -= h[to1] * h[to2]
                                    scale = (
                                        _sigmoid_prime(outputs[to1])
                                        * _sigmoid_prime(outputs[to2])
                                        * total_target
                                        * sum2
                                    )
                                if to1 == to2:
                                    scale += _sigmoid_prime_prime(outputs[to1]) * sum1
                                lower[j1][j2] += wx * (
                                    scale * outputs[from1] * outputs[from2]
                                )
                            elif to1 < to2:
                                tmp = weight_to[to1][to2] - h[to1]
                                if self.censored:
                                    tmp += goal[to2 - first] / share * (
                                        h1[to1] - weight_to[to1][to2]
                                    )
                                extra = errors[to2] if to1 == from2 else 0.0
                                lower[j1][j2] += wx * (
                                    outputs[from1]
                                    * _sigmoid_prime(outputs[to1])
                                    * (
                                        outputs[from2] * probs[to2] * tmp * total_target
                                        + extra
                                    )
                                )
                            else:
                                tmp = weight_to[to2][to1] - h[to2]
                                if self.censored:
                                    tmp += goal[to1 - first] / share * (
                                        h1[to2] - weight_to[to2][to1]
                                    )
                                extra = errors[to1] if to2 == from1 else 0.0
                                lower[j1][j2] += wx * (
                                    outputs[from2]
                                    * _sigmoid_prime(outputs[to2])
                                    * (
                                        outputs[from1] * probs[to1] * tmp * total_target
                                        + extra
                                    )
                                )
            return
        h = [0.0] * nu
        for unit in range(first, nu):
            out = outputs[unit]
            prime = _sigmoid_prime(out)
            target = goal[unit - first]
            if self.linout:
                h[unit] = 2
            elif self.entropy:
                h[unit] = out * (1 - out)
            else:
                h[unit] = _sigmoid_prime_prime(out) * 2 * (out - target) + 2 * prime * prime
        for to1 in range(nu):
            for j1 in range(nconn[to1], nconn[to1 + 1]):
                from1 = conn[j1]
                first1 = to1 < first
                for to2 in range(nu):
                    for j2 in range(nconn[to2], nconn[to2 + 1]):
                        if j2 > j1:
                            continue
                        from2 = conn[j2]
                        first2 = to2 < first
                        if (not first1) and (not first2):
                            if to1 == to2:
                                lower[j1][j2] += wx * (
                                    h[to1] * outputs[from1] * outputs[from2]
                                )
                        elif first1 and first2:
                            sum1 = 0.0
                            sum2 = 0.0
                            for unit in range(first, nu):
                                sum1 += errors[unit] * weight_to[to1][unit]
                                sum2 += weight_to[to1][unit] * weight_to[to2][unit] * h[unit]
                            scale = (
                                _sigmoid_prime(outputs[to1])
                                * _sigmoid_prime(outputs[to2])
                                * sum2
                            )
                            if to1 == to2:
                                scale += _sigmoid_prime_prime(outputs[to1]) * sum1
                            lower[j1][j2] += wx * (scale * outputs[from1] * outputs[from2])
                        elif to1 < to2:
                            extra = errors[to2] if to1 == from2 else 0.0
                            lower[j1][j2] += wx * (
                                outputs[from1]
                                * _sigmoid_prime(outputs[to1])
                                * (outputs[from2] * weight_to[to1][to2] * h[to2] + extra)
                            )
                        else:
                            extra = errors[to1] if to2 == from1 else 0.0
                            lower[j1][j2] += wx * (
                                outputs[from2]
                                * _sigmoid_prime(outputs[to2])
                                * (outputs[from1] * weight_to[to2][to1] * h[to1] + extra)
                            )


def summ2(x, y):
    """Group identical leading columns and sum the rest, as VR_summ2."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    if y.ndim == 1:
        y = y.reshape(-1, 1)
    n, p = x.shape
    rows = np.hstack([x, y])
    if n == 0:
        return x.copy(), y.copy()
    order = np.lexsort(tuple(rows[:, j] for j in range(p - 1, -1, -1)))
    rows = rows[order]
    kept_x = []
    kept_y = []
    acc = rows[0].copy()
    for i in range(1, n):
        if np.any(rows[i, :p] != acc[:p]):
            kept_x.append(acc[:p])
            kept_y.append(acc[p:])
            acc = rows[i].copy()
        else:
            acc[p:] = acc[p:] + rows[i, p:]
    kept_x.append(acc[:p])
    kept_y.append(acc[p:])
    return np.vstack(kept_x), np.vstack(kept_y)
