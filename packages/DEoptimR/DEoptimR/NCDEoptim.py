import numpy as np
from ._core import _bounds, _constraints, _eval, _population


def NCDEoptim(lower, upper, fn, constr=None, meq=0, eps=1e-5, crit=1e-5,
              niche_radius=None, archive_size=100, reinit_if_solu_in_arch=True,
              NP=100, Fl=.1, Fu=1., CRl=0., CRu=1.1, nbngbrsl=None,
              nbngbrsu=None, tau_F=.1, tau_CR=.1, tau_pF=.1,
              tau_nbngbrs=.1, jitter_factor=.001, maxiter=2000,
              add_to_init_pop=None, trace=False, triter=1, **kwargs):
    lo, hi=np.asarray(lower,float),np.asarray(upper,float); d=len(lo)
    nbngbrsl=NP/20 if nbngbrsl is None else nbngbrsl
    nbngbrsu=NP/5 if nbngbrsu is None else nbngbrsu
    args=tuple(kwargs.values()); p=_population(lo,hi,int(NP),add_to_init_pop); NP=p.shape[1]
    F=np.random.uniform(Fl,Fu,NP); CR=np.random.uniform(CRl,CRu,NP); pF=np.random.random(NP)
    nb=np.random.uniform(nbngbrsl,nbngbrsu,NP)
    ev=lambda q: np.array([_eval(fn,q[:,j],args) for j in range(q.shape[1])])
    f=ev(p); h=None; tav=None; mu=None
    if constr is not None:
        h=np.column_stack([_constraints(constr,p[:,j],meq,eps,args) for j in range(NP)])
        tav=np.maximum(h,0).sum(0); mu=np.median(tav)
    archive=[]; radius=np.inf if niche_radius is None else niche_radius
    for it in range(1,int(maxiter)+1):
        if niche_radius is None and NP>1:
            dist=np.full(NP,np.inf)
            for j in range(NP): dist[j]=np.min(np.linalg.norm(p[:,j,None]-np.delete(p,j,axis=1),axis=0))
            radius=min(radius,float(np.mean(dist)))
        trial=p.copy(); Ft=F.copy(); CRt=CR.copy(); pFt=pF.copy()
        for j in range(NP):
            if np.random.random()<=tau_F: Ft[j]=np.random.uniform(Fl,Fu)
            if np.random.random()<=tau_CR: CRt[j]=np.random.uniform(CRl,CRu)
            if np.random.random()<=tau_pF: pFt[j]=np.random.random()
            k=max(3,min(NP-1,int(round(nb[j]))))
            near=np.argsort(np.linalg.norm(p-p[:,j,None],axis=0))[1:k+1]
            r=np.random.choice(near,3,replace=False); base=p[:,r[0]]
            y=base+Ft[j]*(p[:,r[1]]-p[:,r[2]]) if np.random.random()<=pFt[j] else base+.5*(Ft[j]+1)*(p[:,r[1]]+p[:,r[2]]-2*base)
            mask=np.random.random(d)>CRt[j]
            if np.all(mask): mask[np.random.randint(d)]=False
            y[mask]=p[mask,j]; trial[:,j]=_bounds(y,base,lo,hi)
        ft=ev(trial)
        if constr is None: take=ft<=f; ht=None; tv=None
        else:
            ht=np.column_stack([_constraints(constr,trial[:,j],meq,eps,args) for j in range(NP)])
            tv=np.maximum(ht,0).sum(0); take=(tv<=mu)&((tav>mu)|(ft<=f)) | ((tv>mu)&(tv<=tav))
        p[:,take]=trial[:,take]; f[take]=ft[take]; F[take]=Ft[take]; CR[take]=CRt[take]; pF[take]=pFt[take]
        if constr is not None: h[:,take]=ht[:,take]; tav[take]=tv[take]
        for j in np.flatnonzero(take):
            if constr is None or tav[j]<=mu:
                if not any(np.linalg.norm(p[:,j]-a[1])<=radius for a in archive):
                    archive.append((f[j],p[:,j].copy(), None if h is None else h[:,j].copy()))
                    archive.sort(key=lambda x:x[0]); archive=archive[:archive_size]
    order=np.argsort(f) if h is None else np.lexsort((f,tav>0))
    out={"iter":int(maxiter),"solution_pop":p[:,order].copy(),"objective_pop":f[order].copy()}
    if archive:
        out["solution_arch"]=np.column_stack([a[1] for a in archive]); out["objective_arch"]=np.array([a[0] for a in archive])
        if constr is not None: out["constr_value_arch"]=np.column_stack([a[2] for a in archive])
    if constr is not None: out["constr_value_pop"]=h[:,order].copy()
    return out
