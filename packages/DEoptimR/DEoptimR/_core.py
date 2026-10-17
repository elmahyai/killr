"""NumPy implementation of DEoptimR's differential-evolution variants."""
import numpy as np


def _bounds(x, base, lo, hi):
    x = np.array(x, dtype=float, copy=True)
    x[x > hi] = 0.5 * (hi[x > hi] + base[x > hi])
    x[x < lo] = 0.5 * (lo[x < lo] + base[x < lo])
    return x


def _population(lo, hi, npop, extra):
    p = np.random.uniform(lo[:, None], hi[:, None], (len(lo), npop))
    if extra is not None:
        e = np.asarray(extra, dtype=float)
        if e.ndim == 1:
            e = e[:, None]
        p = np.column_stack((p, e))
    return p


def _constraints(constr, p, meq, eps, args):
    h = np.asarray(constr(p, *args), dtype=float).reshape(-1)
    if meq:
        h[:meq] = np.abs(h[:meq]) - np.asarray(eps)
    return h


def _eval(fn, p, args):
    return float(fn(np.asarray(p), *args))


def _best(f, tav=None, mu=None):
    if tav is None:
        return int(np.argmin(f))
    feasible = tav <= mu
    return int(np.flatnonzero(feasible)[np.argmin(f[feasible])]) if np.any(feasible) else int(np.argmin(tav))


def jdeoptim(lower, upper, fn, constr=None, meq=0, eps=1e-5, NP=None,
             Fl=.1, Fu=1., tau_F=.1, tau_CR=.1, tau_pF=.1,
             jitter_factor=.001, tol=1e-15, maxiter=None, fnscale=1.,
             compare_to="median", add_to_init_pop=None, trace=False,
             triter=1, details=False, args=()):
    lo, hi = np.asarray(lower, float), np.asarray(upper, float)
    d = len(lo); NP = 10*d if NP is None else int(NP)
    maxiter = 2000*d if maxiter is None else int(maxiter)
    p = _population(lo, hi, NP, add_to_init_pop); NP = p.shape[1]
    jitter = jitter_factor is not None
    F = ((1 + jitter_factor*np.random.uniform(-.5, .5, d))[:, None] *
         np.random.uniform(Fl, Fu, (1, NP))) if jitter else np.random.uniform(Fl, Fu, (1, NP))
    CR, pF = np.random.random(NP), np.random.random(NP)
    f = np.array([_eval(fn, p[:, j], args) for j in range(NP)])
    h = tav = mu = None
    if constr is not None:
        h = np.column_stack([_constraints(constr, p[:, j], meq, eps, args) for j in range(NP)])
        tav, mu = np.maximum(h, 0).sum(axis=0), np.median(np.maximum(h, 0).sum(axis=0))
    def conv():
        b = _best(f, tav, mu)
        c = np.median(f) if compare_to == "median" else np.max(f)
        return (c-f[b])/fnscale, b
    convergence, it = 0, 0
    cv, best = conv()
    while cv > tol or (h is not None and np.any(h[:, best] > 0)):
        if it >= maxiter:
            convergence = 1; break
        it += 1
        for j in range(NP):
            i = (it + j) % NP
            if np.random.random() <= tau_F:
                ft = np.random.uniform(Fl, Fu) * ((1+jitter_factor*np.random.uniform(-.5,.5,d)) if jitter else 1)
            else: ft = F[:, i]
            crt = np.random.random() if np.random.random() <= tau_CR else CR[i]
            pft = np.random.random() if np.random.random() <= tau_pF else pF[i]
            choices = np.delete(np.arange(NP), i)
            r = np.random.choice(choices, 3, replace=False)
            base, x1, x2 = p[:, r[0]], p[:, r[1]], p[:, r[2]]
            trial = base + ft*(x1-x2) if np.random.random() <= pft else base + .5*(ft+1)*(x1+x2-2*base)
            ignore = np.random.random(d) > crt
            if np.all(ignore): ignore[np.random.randint(d)] = False
            trial[ignore] = p[ignore, i]; trial = _bounds(trial, base, lo, hi)
            ht = _constraints(constr, trial, meq, eps, args) if constr is not None else None
            tv = np.maximum(ht, 0).sum() if ht is not None else None
            accept = (tv <= tav[i] if tv is not None and tav[i] > mu else
                      tv <= mu if tv is not None else False)
            if ht is None: accept = _eval(fn, trial, args) <= f[i]
            elif tv <= mu and tav[i] <= mu: accept = _eval(fn, trial, args) <= f[i]
            if accept:
                p[:, i], F[:, i], CR[i], pF[i], f[i] = trial, np.asarray(ft).reshape(-1) if np.ndim(ft) else ft, crt, pft, _eval(fn, trial, args)
                if ht is not None: h[:, i], tav[i] = ht, tv
        cv, best = conv()
    out = {"par": p[:, best].copy(), "value": float(f[best]), "iter": it, "convergence": convergence}
    if details: out.update(poppar=p.copy(), popcost=f.copy())
    return out
