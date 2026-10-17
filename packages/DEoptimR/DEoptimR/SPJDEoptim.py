import numpy as np
from ._core import _bounds, _constraints, _eval, _population


def SPJDEoptim(lower, upper, fn, constr=None, meq=0, eps=1e-5,
               sequential_eval="none", further_args=None, NP=None, Fl=.1,
               Fu=1., CRl=0., CRu=1.1, tau_F=.1, tau_CR=.1, tau_pF=.1,
               jitter_factor=.001, tol=1e-15, maxiter=None, fnscale=1.,
               compare_to="median", add_to_init_pop=None, trace=False,
               triter=1, details=False, **kwargs):
    lo, hi = np.asarray(lower, float), np.asarray(upper, float)
    d = len(lo); NP = 10*d if NP is None else int(NP)
    maxiter = 2000*d if maxiter is None else int(maxiter)
    args = tuple((further_args or {}).values())
    p = _population(lo, hi, NP, add_to_init_pop); NP = p.shape[1]
    jitter = jitter_factor is not None
    F = ((1+jitter_factor*np.random.uniform(-.5,.5,d))[:,None] *
         np.random.uniform(Fl, Fu, (1,NP))) if jitter else np.random.uniform(Fl,Fu,(1,NP))
    CR, pF = np.random.uniform(CRl, CRu, NP), np.random.random(NP)
    def ev(pop): return np.array([_eval(fn, pop[:,j], args) for j in range(pop.shape[1])])
    f = ev(p); h = tav = mu = None
    if constr is not None:
        h = np.column_stack([_constraints(constr,p[:,j],meq,eps,args) for j in range(NP)])
        tav = np.maximum(h,0).sum(0); mu = np.median(tav)
    it = 0
    def best():
        feas = np.ones(NP,bool) if h is None else tav <= mu
        return np.flatnonzero(feas)[np.argmin(f[feas])] if np.any(feas) else np.argmin(tav)
    def criterion():
        b=best(); c=np.median(f) if compare_to=="median" else np.max(f)
        return (c-f[b])/fnscale, b
    cv,b = criterion()
    while cv > tol or (h is not None and np.any(h[:,b]>0)):
        if it >= maxiter: break
        it += 1; trial=p.copy(); Ft=F.copy(); CRt=CR.copy(); pFt=pF.copy()
        for j in range(NP):
            if np.random.random() <= tau_F: Ft[:,j] = np.random.uniform(Fl,Fu)*(1+jitter_factor*np.random.uniform(-.5,.5,d) if jitter else 1)
            if np.random.random() <= tau_CR: CRt[j]=np.random.uniform(CRl,CRu)
            if np.random.random() <= tau_pF: pFt[j]=np.random.random()
            r=np.random.choice(np.delete(np.arange(NP),j),3,replace=False)
            x=p[:,j]; base=p[:,r[0]]; a=p[:,r[1]]; z=p[:,r[2]]
            y=base+Ft[:,j]*(a-z) if np.random.random()<=pFt[j] else base+.5*(Ft[:,j]+1)*(a+z-2*base)
            mask=np.random.random(d)>CRt[j]
            if np.all(mask): mask[np.random.randint(d)]=False
            y[mask]=x[mask]; trial[:,j]=_bounds(y,base,lo,hi)
        ft=ev(trial)
        if constr is None:
            take=ft<=f
        else:
            ht=np.column_stack([_constraints(constr,trial[:,j],meq,eps,args) for j in range(NP)])
            tv=np.maximum(ht,0).sum(0); take=(tv<=mu)&((tav>mu)|(ft<=f)) | ((tv>mu)&(tv<=tav))
            p_h=ht
        p[:,take]=trial[:,take]; f[take]=ft[take]; F[:,take]=Ft[:,take]; CR[take]=CRt[take]; pF[take]=pFt[take]
        if constr is not None: h[:,take]=p_h[:,take]; tav[take]=tv[take]
        cv,b=criterion()
    out={"par":p[:,b].copy(),"value":float(f[b]),"iter":it,"convergence":int(it>=maxiter)}
    if details: out.update(poppar=p.copy(),popcost=f.copy())
    return out
