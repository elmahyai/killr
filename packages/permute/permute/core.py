"""Python translation of permute's permutation-design primitives."""
from __future__ import annotations
from dataclasses import dataclass, field
import math
import numpy as np

@dataclass
class Within:
    type: str = "free"
    constant: bool = False
    mirror: bool = False
    ncol: int | None = None
    nrow: int | None = None

@dataclass
class Plots:
    strata: object = None
    type: str = "none"
    mirror: bool = False
    ncol: int | None = None
    nrow: int | None = None

@dataclass
class Blocks:
    strata: object = None

@dataclass
class How:
    within: Within = field(default_factory=Within)
    plots: Plots = field(default_factory=Plots)
    blocks: object = None
    nperm: int = 199
    complete: bool = False
    maxperm: int = 9999
    minperm: int = 5040
    all_perms: object = None
    make: bool = True
    observed: bool = False

class PermutationMatrix(np.ndarray):
    """ndarray carrying the design metadata used by permute."""
    def __new__(cls, x, control=None, observed=None):
        obj = np.asarray(x, dtype=int).view(cls)
        obj.control, obj.observed = control, observed
        return obj
    def __array_finalize__(self, obj):
        if obj is None: return
        self.control = getattr(obj, "control", None)
        self.observed = getattr(obj, "observed", None)

class AllPerms(PermutationMatrix): pass

def _as_how(x=None): return x if isinstance(x, How) else how()
def _nobs(x):
    if np.isscalar(x): return int(x)
    a=np.asarray(x); return int(a.shape[0] if a.ndim else a.size)
def nobs(object):
    """Return the number of observations, with scalar R vectors length one."""
    if np.isscalar(object):
        return 1
    return _nobs(object)

def how(within=None, plots=None, blocks=None, nperm=199, complete=False,
        maxperm=9999, minperm=5040, all_perms=None, make=True, observed=False, **kwargs):
    return How(within=_as_within(within), plots=_as_plots(plots), blocks=blocks,
               nperm=nperm, complete=complete, maxperm=maxperm, minperm=minperm,
               all_perms=all_perms, make=make, observed=observed)
def _as_within(x): return x if isinstance(x, Within) else Within() if x is None else Within(**x)
def _as_plots(x): return x if isinstance(x, Plots) else Plots() if x is None else Plots(**x)

def _strata_values(s):
    if s is None: return None
    return np.asarray(s)
def _levels(s):
    a=_strata_values(s); return np.unique(a, return_index=True)[0] if a is not None else np.array([])
def _counts(s):
    a=_strata_values(s); return np.array([np.sum(a==v) for v in _levels(a)], dtype=int)

def getBlocks(object, **kwargs): return object.blocks
getWithin=lambda object, **kwargs: object.within
getPlots=lambda object, **kwargs: object.plots
def getStrata(object, which="plots", drop=True, **kwargs):
    return object.plots.strata if which == "plots" else object.blocks
def getType(object, which="plots", **kwargs): return (object.plots if which=="plots" else object.within).type
def getMirror(object, which="plots", **kwargs): return (object.plots if which=="plots" else object.within).mirror
def getConstant(object, **kwargs): return object.within.constant
def getRow(object, which="plots", **kwargs):
    if isinstance(object, (Within, Plots)): return object.nrow
    return (object.plots if which=="plots" else object.within).nrow
def getCol(object, which="plots", **kwargs):
    if isinstance(object, (Within, Plots)): return object.ncol
    return (object.plots if which=="plots" else object.within).ncol
def getDim(object, which="plots", **kwargs):
    row, col = getRow(object, which), getCol(object, which)
    return None if row is None and col is None else np.array([row, col])
def getNperm(object, **kwargs): return object.nperm
def getMaxperm(object, **kwargs): return object.maxperm
def getMinperm(object, **kwargs): return object.minperm
def getComplete(object, **kwargs): return object.complete
def getMake(object, **kwargs): return object.make
def getObserved(object, **kwargs): return object.observed
def getAllperms(object, **kwargs): return object.all_perms
def getControl(object, **kwargs): return getattr(object, "control", object)
def getHow(object, **kwargs): return getControl(object)

def _set(obj, name, value):
    if isinstance(obj, How) and name in ("within","plots"): value = _as_within(value) if name=="within" else _as_plots(value)
    setattr(obj,name,value); return obj
setBlocks = lambda object,value: _set(object,"blocks",value)
setWithin = lambda object,value: _set(object,"within",_as_within(value))
def setStrata(object, value):
    if isinstance(object, (Within, Plots)):
        return _set(object, "strata", value)
    object.plots.strata = value
    return object
setType = lambda object,value: _set(object,"type",str(value))
setMirror = lambda object,value: _set(object,"mirror",None if value is None else bool(value))
setConstant = lambda object,value: _set(object,"constant",None if value is None else bool(value))
def setPlots(object, value):
    if not isinstance(value, Plots):
        raise TypeError("value must be a Plots object")
    return _set(object, "plots", value)
def _set_dimension(object, name, value):
    if isinstance(object, How):
        raise TypeError(f"set{name.title()} cannot be used directly on How objects")
    return _set(object, name, None if value is None else int(value))
def setRow(object,value): return _set_dimension(object, "nrow", value)
def setCol(object,value): return _set_dimension(object, "ncol", value)
def setDim(object,value):
    value = list(value)
    if len(value) != 2:
        raise ValueError("dimension must have length 2")
    setRow(object, value[0]); setCol(object, value[1])
    return object
setNperm=lambda object,value:_set(object,"nperm",int(value))
setMaxperm=lambda object,value:_set(object,"maxperm",int(value))
setMinperm=lambda object,value:_set(object,"minperm",int(value))
setComplete=lambda object,value:_set(object,"complete",None if value is None else bool(value))
setMake=lambda object,value:_set(object,"make",None if value is None else bool(value))
setObserved=lambda object,value:_set(object,"observed",None if value is None else bool(value))
def setAllperms(object,value):
    object.all_perms = None if value is None else as_allPerms(value, object)
    return object

def shuffleFree(x,size=None,rng=None):
    rng=np.random.default_rng() if rng is None else rng
    a=np.arange(1,int(x)+1) if np.isscalar(x) else np.asarray(x)
    return rng.choice(a, size if size is not None else len(a), replace=False)
def shuffleSeries(x,mirror=False,start=None,flip=None,rng=None):
    rng=np.random.default_rng() if rng is None else rng; a=np.asarray(x); n=len(a)
    start=int(shuffleFree(n,1,rng)[0]) if start is None else int(start)
    out=(np.arange(start,start+n)%n)
    if mirror and ((bool(flip) if flip is not None else rng.random()<.5)): out=out[::-1]
    return a[out]
def shuffleGrid(nrow,ncol,mirror=False,start_row=None,start_col=None,flip=None,rng=None,**kwargs):
    rng=np.random.default_rng() if rng is None else rng
    sr=int(shuffleFree(nrow,1,rng)[0]) if start_row is None else int(start_row); sc=int(shuffleFree(ncol,1,rng)[0]) if start_col is None else int(start_col)
    ir=np.arange(sr,sr+nrow)%nrow; ic=np.arange(sc,sc+ncol)%ncol
    f=rng.random(2)<.5 if flip is None else np.asarray(flip,dtype=bool)
    if mirror:
        if f[0]: ir=ir[::-1]
        if f[1]: ic=ic[::-1]
    return np.repeat(ic,nrow)*nrow+np.tile(ir,ncol)+1
def shuffleStrata(strata,type,mirror=False,start=None,flip=None,nrow=None,ncol=None,start_row=None,start_col=None,rng=None):
    a=np.asarray(strata); lev=np.unique(a); out=np.arange(len(a));
    if type=="free": p=shuffleFree(len(lev),rng=rng)
    elif type=="series": p=shuffleSeries(np.arange(1,len(lev)+1),mirror,start,flip,rng)
    elif type=="grid": p=shuffleGrid(nrow,ncol,mirror,start_row,start_col,flip,rng)
    else: raise ValueError("Invalid permutation type")
    for i,v in enumerate(lev): out[a==v]=np.flatnonzero(a==lev[p[i]-1])
    return out+1
def _shuffle_no_strata(n, control, rng=None):
    t=control.within.type
    if t == "free": return shuffleFree(n, n, rng)
    if t == "series": return shuffleSeries(np.arange(1, n+1), control.within.mirror, rng=rng)
    if t == "grid": return shuffleGrid(control.within.nrow, control.within.ncol, control.within.mirror, rng=rng)
    if t == "none": return np.arange(1, n+1)
    raise ValueError("Invalid permutation type")
def shuffle(n,control=None,rng=None):
    c=_as_how(control); N=_nobs(n); return _shuffle_no_strata(N,c,rng)
def shuffleSet(n,nset,control=None,check=True,quietly=False,rng=None):
    c=_as_how(control); return np.vstack([shuffle(n,c,rng) for _ in range(int(nset))])

def numPerms(object,control=None):
    c=_as_how(control); n=_nobs(object); tp,tw=c.plots.type,c.within.type; s=c.plots.strata
    if s is None: tab=np.array([n])
    else: tab=_counts(s)
    np_=math.factorial(len(tab)) if tp=="free" else (len(tab)*(4 if c.plots.ncol and c.plots.ncol>2 else 2) if tp in ("series","grid") and c.plots.mirror else (len(tab) if tp in ("series","grid") else 1))
    if tw=="none": nw=1
    elif tw=="free": nw=math.factorial(tab[0]) if s is not None and c.within.constant else (math.prod(math.factorial(int(x)) for x in tab) if s is not None else math.factorial(n))
    else: nw=(2 if c.within.mirror else 1)*n if s is None else math.prod(int(x)*(2 if c.within.mirror else 1) for x in tab)
    return float(np_*nw)

def allFree(n,v=None):
    a=np.arange(1,int(n)+1) if v is None else np.asarray(v)
    if len(a)==1:return a.reshape(1,1)
    return np.vstack([np.column_stack((np.full(math.factorial(len(a)-1),x),allFree(len(a)-1,a[a!=x]))) for x in a])
def allSeries(n,nperms,mirror=False):
    # R's allSeries: row i (1-based) is seq(i, length = n) %% n + 1, so row n is the identity.
    n=int(n); X=np.vstack([np.roll(np.arange(1,n+1),-(i%n)) for i in range(1,n+1)])
    if mirror and nperms>2:X=np.vstack((X,X[:,::-1]))
    return X[:int(nperms)]
def allGrid(n,nperms,nrow,ncol,mirror=False,constant=False):
    if ncol==2:return allSeries(n,nperms,mirror)
    rows=[]
    for i in range(nrow):
      for j in range(ncol):
       ir=np.roll(np.arange(nrow),-i); ic=np.roll(np.arange(ncol),-j); rows.append(np.repeat(ic,nrow)*nrow+np.tile(ir,ncol)+1)
    X=np.asarray(rows)
    if mirror:X=np.vstack((X,X[:,::-1]))
    return X[:int(nperms)]
def allStrata(n,control):
    c=_as_how(control); s=np.asarray(c.plots.strata); lev=np.unique(s); p=allFree(len(lev)) if c.plots.type=="free" else allSeries(len(lev),int(numPerms(len(lev),How(within=Within(type=c.plots.type)))),c.plots.mirror)
    return np.vstack([np.concatenate([np.flatnonzero(s==lev[j])+1 for j in row]) for row in p])
def allPerms(n,control=None,check=True):
    c=_as_how(control); N=_nobs(n); tp=c.within.type
    p=allFree(N) if tp=="free" else allSeries(N,int(numPerms(N,c)),c.within.mirror) if tp=="series" else allGrid(N,int(numPerms(N,c)),c.within.nrow,c.within.ncol,c.within.mirror,c.within.constant) if tp=="grid" else np.arange(1,N+1).reshape(1,-1)
    if not c.observed:p=p[~np.all(p==np.arange(1,N+1),axis=1)]
    return AllPerms(p,c,c.observed)
def as_allPerms(object,control=None): return AllPerms(np.asarray(object),control,getObserved(control) if control else None)
def permute(i,n,control):
    # Draws come from the ported R RNG (shuffle.py), so set.seed reproduces R's permute().
    from .shuffle import shuffle as _ported_shuffle  # lazy: shuffle.py imports this module
    c=_as_how(control); return np.asarray(c.all_perms[int(i)-1] if c.complete and c.all_perms is not None else _ported_shuffle(n,c))
def check(object,control=None,quietly=False):
    c=_as_how(control); np_=numPerms(object,c); c.complete=bool(c.complete or np_-int(not c.observed)<=c.nperm or np_-int(not c.observed)<c.minperm)
    if c.complete and c.make:c.all_perms=allPerms(object,c,False); c.nperm=len(c.all_perms)
    return {"n":np_,"control":c}
