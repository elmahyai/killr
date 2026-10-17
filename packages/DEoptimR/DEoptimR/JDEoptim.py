import numpy as np
from ._core import jdeoptim


def JDEoptim(lower, upper, fn, constr=None, meq=0, eps=1e-5, NP=None,
             Fl=.1, Fu=1., tau_F=.1, tau_CR=.1, tau_pF=.1,
             jitter_factor=.001, tol=1e-15, maxiter=None, fnscale=1.,
             compare_to="median", add_to_init_pop=None, trace=False,
             triter=1, details=False, **kwargs):
    return jdeoptim(lower, upper, fn, constr, meq, eps, NP, Fl, Fu, tau_F,
                    tau_CR, tau_pF, jitter_factor, tol, maxiter, fnscale,
                    compare_to, add_to_init_pop, trace, triter, details,
                    tuple(kwargs.values()))
