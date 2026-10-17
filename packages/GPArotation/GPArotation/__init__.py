from .core import criterion, GPForth, GPFoblq, eiv, echelon
from .core import Random_Start as _random_start
from .core import lpT, lpQ, GPForth_lp, GPFoblq_lp
import numpy as np

_ENGINE_ARGS = ("eps", "maxit", "algorithm", "fwindow")


def _engine_args(kw):
    """The engine arguments of GPFoblq/GPForth (R's eps, maxit, algorithm, fwindow)."""
    return {k: v for k, v in kw.items() if k in _ENGINE_ARGS}


def _orth(method, A, Tmat=None, normalize=False, **kw):
    return GPForth(A, Tmat=Tmat, normalize=normalize, method=method, methodArgs=kw or None)


def _oblique(method, A, Tmat=None, normalize=False, **kw):
    return GPFoblq(A, Tmat=Tmat, normalize=normalize, method=method, methodArgs=kw or None)


def GPFRSorth(A, **kw): return GPForth(A, **kw)
def GPFRSoblq(A, **kw): return GPFoblq(A, **kw)
def Random_Start(k=2): return _random_start(k)


def oblimin(A, Tmat=None, gam=0, normalize=False, **kw): return _oblique("oblimin", A, Tmat, normalize, gam=gam)
def quartimin(A, Tmat=None, normalize=False, **kw): return _oblique("quartimin", A, Tmat, normalize)
def targetT(A, Tmat=None, Target=None, normalize=False, **kw): return _orth("target", A, Tmat, normalize, Target=Target)
def targetQ(A, Tmat=None, Target=None, normalize=False, **kw): return _oblique("target", A, Tmat, normalize, Target=Target)
def pstT(A, Tmat=None, W=None, Target=None, normalize=False, **kw): return _orth("pst", A, Tmat, normalize, W=W, Target=Target)
def pstQ(A, Tmat=None, W=None, Target=None, normalize=False, **kw): return _oblique("pst", A, Tmat, normalize, W=W, Target=Target)
def oblimax(A, Tmat=None, normalize=False, **kw): return GPFoblq(A, Tmat=Tmat, normalize=normalize, method="oblimax", **_engine_args(kw))
def binormamin(A, Tmat=None, normalize=False, **kw): return _oblique("binormamin", A, Tmat, normalize)
def entropy(A, Tmat=None, normalize=False, **kw): return _orth("entropy", A, Tmat, normalize)
def quartimax(A, Tmat=None, normalize=False, **kw): return _orth("quartimax", A, Tmat, normalize)
def Varimax(A, Tmat=None, normalize=False, **kw): return _orth("varimax", A, Tmat, normalize)
def simplimax(A, Tmat=None, k=None, normalize=False, **kw): return _oblique("simplimax", A, Tmat, normalize, k=k or A.shape[0]*(A.shape[1]-1))
def bentlerT(A, Tmat=None, normalize=False, **kw): return _orth("bentler", A, Tmat, normalize)
def bentlerQ(A, Tmat=None, normalize=False, **kw): return _oblique("bentler", A, Tmat, normalize)
def tandemI(A, Tmat=None, normalize=False, **kw): return _orth("tandemI", A, Tmat, normalize)
def tandemII(A, Tmat=None, normalize=False, **kw): return _orth("tandemII", A, Tmat, normalize)
def geominT(A, Tmat=None, delta=.01, normalize=False, **kw): return _orth("geomin", A, Tmat, normalize, delta=delta)
def geominQ(A, Tmat=None, delta=.01, normalize=False, **kw): return _oblique("geomin", A, Tmat, normalize, delta=delta)
def bigeominT(A, Tmat=None, delta=.01, normalize=False, **kw): return _orth("bigeomin", A, Tmat, normalize, delta=delta)
def bigeominQ(A, Tmat=None, delta=.01, normalize=False, **kw): return _oblique("bigeomin", A, Tmat, normalize, delta=delta)
def cfT(A, Tmat=None, kappa=0, normalize=False, **kw): return _orth("cf", A, Tmat, normalize, kappa=kappa)
def cfQ(A, Tmat=None, kappa=0, normalize=False, **kw): return _oblique("cf", A, Tmat, normalize, kappa=kappa)
def infomaxT(A, Tmat=None, normalize=False, **kw): return _orth("infomax", A, Tmat, normalize)
def infomaxQ(A, Tmat=None, normalize=False, **kw): return _oblique("infomax", A, Tmat, normalize)
def mccammon(A, Tmat=None, normalize=False, **kw): return _orth("mccammon", A, Tmat, normalize)
def bifactorT(A, Tmat=None, normalize=False, **kw): return _orth("bifactor", A, Tmat, normalize)
def bifactorQ(A, Tmat=None, normalize=False, **kw): return GPFoblq(A, Tmat=Tmat, normalize=normalize, method="bifactor", **_engine_args(kw))
def equamax(A, Tmat=None, kappa=None, normalize=False, **kw): return _orth("cf", A, Tmat, normalize, kappa=A.shape[1]/(2*A.shape[0]) if kappa is None else kappa)
def parsimax(A, Tmat=None, kappa=None, normalize=False, **kw): return _orth("cf", A, Tmat, normalize, kappa=(A.shape[1]-1)/(A.shape[1]+A.shape[0]-2) if kappa is None else kappa)
def varimin(A, Tmat=None, normalize=False, **kw): return _orth("varimin", A, Tmat, normalize)
__all__ = [n for n in globals() if not n.startswith("_")]
