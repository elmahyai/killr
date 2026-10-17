"""NumPy implementation of GPArotation's numerical routines."""
import math
import time

import numpy as np


def _out(g, f, method):
    return {"Gq": np.asarray(g, float), "f": float(f), "Method": method}


def _lsum(x, axis=None):
    """R's sum, colSums, and rowSums: accumulate in long double, return double (LDOUBLE)."""
    return np.sum(np.asarray(x, float).astype(np.longdouble), axis=axis).astype(float)


def criterion(L, method, methodArgs=None):
    """Evaluate a GPArotation vgQ criterion."""
    L = np.asarray(L, float)
    a = methodArgs or {}
    s = L * L
    p, k = L.shape
    m = method.lower().replace("_", ".")
    if m in ("quartimin",):
        x = s @ (np.ones((k, k)) - np.eye(k))
        return _out(L*x, np.sum(s*x)/4, "Quartimin")
    if m == "oblimin":
        gam = a.get("gam", 0)
        x = s.sum(1, keepdims=True) - s
        if gam != 0: x -= (gam/p)*x.sum(0, keepdims=True)
        name = "Oblimin Quartimin" if gam == 0 else ("Oblimin Biquartimin" if gam == .5 else f"Oblimin gamma = {gam}")
        return _out(L*x, np.sum(s*x)/4, name)
    if m == "cf":
        q = a.get("kappa", 0)
        rn, cn = s.sum(1, keepdims=True), s.sum(0, keepdims=True)
        xrow, xcol = rn-s, cn-s
        f = (1-q)*np.sum(s*xrow)/4 + q*np.sum(s*xcol)/4
        name = "Crawford-Ferguson Quartimax/Quartimin" if q == 0 else ("Crawford-Ferguson Varimax" if q == 1/p else ("Equamax" if q == k/(2*p) else ("Parsimax" if q == (k-1)/(p+k-2) else ("Factor Parsimony" if q == 1 else f"Crawford-Ferguson: kappa={q}"))))
        return _out((1-q)*L*xrow + q*L*xcol, f, name)
    if m == "target":
        t = np.asarray(a["Target"], float)
        g = 2*(L-t); g = np.nan_to_num(g)
        return _out(g, np.nansum((L-t)**2), "Target rotation")
    if m == "pst":
        w, t = np.asarray(a["W"], float), np.asarray(a["Target"], float)
        return _out(2*w*L-2*w*t, np.sum((w*L-w*t)**2), "Partially specified target")
    if m == "entropy":
        z = np.log(s + np.finfo(float).eps)
        return _out(-(L*z+L), -np.sum(s*z)/2, "Minimum entropy")
    if m == "infomax":
        eps = np.finfo(float).eps; total = s.sum(); e = s/total
        r, c = s.sum(1)/total, s.sum(0)/total
        q0, q1, q2 = -np.sum(e*np.log(e+eps)), -np.sum(r*np.log(r+eps)), -np.sum(c*np.log(c+eps))
        h = -(np.log(e+eps)+1); h1 = -(np.log(r+eps)+1); h2 = -(np.log(c+eps)+1)
        g0 = (h-np.sum(s*h)/total)/total
        g1 = (h1[:,None]-np.sum(s.sum(1)*h1)/total)/total
        g2 = (h2[None,:]-np.sum(s.sum(0)*h2)/total)/total
        return _out(2*L*(g0-g1-g2), np.log(k)+q0-q1-q2, "Infomax")
    if m == "mccammon":
        eps=np.finfo(float).eps; cs=s.sum(0); total=s.sum(); P=s/cs
        lp=np.where(P>0,np.log(P),0); q1=-np.sum(P*lp)
        p2=cs/total; l2=np.where(p2>0,np.log(p2),0); q2=-np.sum(p2*l2)
        h1=-(lp+1); al1=np.sum(P*h1,axis=0)
        g1=(h1-al1)/cs
        h2=-(l2+1); al2=np.sum(p2*h2); g2=np.broadcast_to((h2-al2)/total,(p,k))
        return _out(2*L*(g1/q1-g2/q2), np.log(q1)-np.log(q2), "McCammon entropy")
    if m == "geomin":
        d=a.get("delta",.01); z=s+d; pro=np.exp(np.mean(np.log(z),axis=1))
        return _out((2/k)*(L/z)*pro[:,None], pro.sum(), "Geomin")
    if m == "simplimax":
        n=a.get("k",p*(k-1)); mask=np.zeros(L.size,bool); mask[np.argsort(s.ravel(order="F"))[:n]]=1; mask=mask.reshape((p,k),order="F")
        return _out(2*mask*L, np.sum(s[mask]), f"Simplimax (k={n})")
    if m == "bifactor":
        z=s[:,1:]; rs=_lsum(z,axis=1); g=4*L[:,1:]*(rs[:,None]-z)
        return _out(np.column_stack((np.zeros(p),g)), _lsum(rs*rs)-_lsum(z*z), "Bifactor Biquartimin")
    if m == "bigeomin":
        q=criterion(L[:,1:],"geomin",a); return _out(np.column_stack((np.zeros(p),q["Gq"])),q["f"],"Bi-Geomin")
    if m in ("tandemi", "tandem1"):
        ll=L@L.T; ll2=ll*ll; mp=ll2@s
        return _out(-(4*L*mp+4*(ll*(s@s.T))@L), -np.sum(s*mp), "Tandem I")
    if m in ("tandemii", "tandem2"):
        ll=L@L.T; ill2=1-ll*ll; mp=ill2@s
        return _out(4*L*mp-4*(ll*(s@s.T))@L, np.sum(s*mp), "Tandem II")
    if m == "oblimax":
        # R uses L^4 and L^3 through C pow, sums in long double, and log from libm.
        # np.power takes a SIMD path that differs by one ulp, so np.float_power (C pow) is used.
        s2=_lsum(s); s4=_lsum(np.float_power(L,4.0))
        return _out(-(4*np.float_power(L,3.0)/s4-4*L/s2),-(math.log(s4)-2*math.log(s2)),"Oblimax")
    if m == "bentler":
        M=s.T@s; d=np.diag(M); ld=np.linalg.slogdet(M)
        f=-(ld[1]-np.log(d).sum())/4
        return _out(-L*(s@(np.linalg.inv(M)-np.diag(1/d))),f,"Bentler")
    if m == "quartimax":
        return _out(-L**3,-np.sum(L**4)/4,"Quartimax")
    if m == "varimax":
        q=s-s.mean(0,keepdims=True); return _out(-L*q,-np.sum(q*q)/4,"Varimax")
    if m == "binormamin":
        u=s.sum(0); inv=1/u; n=s.T@s; c=n/np.outer(u,u); f=c.sum()-np.trace(c)
        lsu=s*inv; t1=(lsu.sum(1,keepdims=True)-lsu)*inv
        nou=n*inv[None,:]; t2=(nou.sum(1)-np.diag(nou))*inv**2
        return _out(4*L*(t1-t2[None,:]),f,"Binormamin")
    if m == "varimin":
        q=s-s.mean(0,keepdims=True); return _out(L*q,np.sum(q*q)/4,"Varimin")
    if m == "lp.wls":
        w=np.asarray(a["W"]); return _out(2*w*L/p,np.sum(w*L*L)/p,"Weighted least squares for Lp rotation")
    raise ValueError(f"unknown GPArotation method: {method}")


def _normalize(A, normalize):
    if normalize is False: return np.asarray(A,float), None
    w = np.asarray(normalize,float) if not isinstance(normalize,(bool,np.bool_)) else np.sqrt(np.sum(np.asarray(A)**2,axis=1))
    return np.asarray(A,float)/w[:,None], w


def GPForth(A, Tmat=None, normalize=False, eps=1e-5, maxit=2000, method="varimax", methodArgs=None, algorithm="bb", fwindow=10):
    A,w=_normalize(A,normalize); p,k=A.shape; T=np.eye(k) if Tmat is None else np.asarray(Tmat,float).copy()
    alpha=1.; prevT=prevG=None; rows=[]
    for it in range(maxit+1):
        L=A@T; q=criterion(L,method,methodArgs); G=A.T@q["Gq"]; M=T.T@G; Gp=G-T@((M+M.T)/2); sn=np.linalg.norm(Gp); rows.append([it,q["f"],np.log10(sn) if sn else -np.inf,alpha])
        if sn<eps: break
        if algorithm=="bb" and prevT is not None:
            den=abs(np.sum((Gp-prevG)*(T-prevT))); alpha=np.clip(np.sum((T-prevT)**2)/den if den else alpha,1e-10,20)
        else: alpha*=2
        target=max(x[1] for x in rows[max(0,len(rows)-int(fwindow)):])
        for _ in range(11):
            X=T-alpha*Gp; u,_,vh=np.linalg.svd(X,full_matrices=False); Tn=u@vh; qn=criterion(A@Tn,method,methodArgs)
            if target-qn["f"]>.5*sn*sn*alpha: break
            alpha/=2
        prevT,prevG,T=T,Gp,Tn
    out={"loadings":A@T,"Th":T,"Table":np.array(rows),"method":q["Method"],"methodName":method,"orthogonal":True,"convergence":sn<eps,"Gq":qn["Gq"] if 'qn' in locals() else q["Gq"]}
    if w is not None: out["loadings"]*=w[:,None]
    return out


def GPFoblq(A, Tmat=None, normalize=False, eps=1e-5, maxit=2000, method="quartimin", methodArgs=None, algorithm="bb", fwindow=10):
    A,w=_normalize(A,normalize); p,k=A.shape; T=np.eye(k) if Tmat is None else np.asarray(Tmat,float).copy(); alpha=1.; prevT=prevG=None; rows=[]
    for it in range(maxit+1):
        Ti=np.linalg.inv(T); L=A@Ti.T; q=criterion(L,method,methodArgs); G=-((L.T@q["Gq"]@Ti).T); Gp=G-T*_lsum(T*G,axis=0)[None,:]; sn=np.sqrt(_lsum(Gp*Gp)); rows.append([it,q["f"],np.log10(sn) if sn else -np.inf,alpha])
        if sn<eps: break
        if algorithm=="bb" and prevT is not None:
            den=abs(_lsum((Gp-prevG)*(T-prevT))); alpha=np.clip(_lsum((T-prevT)**2)/den if den else alpha,1e-10,20)
        else: alpha*=2
        target=max(x[1] for x in rows[max(0,len(rows)-int(fwindow)):])
        for _ in range(11):
            X=T-alpha*Gp; v=1/np.sqrt(_lsum(X*X,axis=0)); Tn=X*v[None,:]; Lin=A@np.linalg.inv(Tn).T; qn=criterion(Lin,method,methodArgs)
            if target-qn["f"]>.5*sn*sn*alpha: break
            alpha/=2
        prevT,prevG,T=T,Gp,Tn
    out={"loadings":A@np.linalg.inv(T).T,"Phi":T.T@T,"Th":T,"Table":np.array(rows),"method":q["Method"],"methodName":method,"orthogonal":False,"convergence":sn<eps,"Gq":qn["Gq"] if 'qn' in locals() else q["Gq"]}
    if w is not None: out["loadings"]*=w[:,None]
    return out


def _lp_weights(L, p, eps):
    return (L * L + eps) ** (p / 2 - 1)


def GPForth_lp(A, Tmat=None, p=1, normalize=False, eps=1e-5, maxit=10000, gpaiter=5):
    """R GPForth.lp: orthogonal Lp rotation, an outer IRLS loop around GPForth(method='lp.wls')."""
    A = np.asarray(A, float)
    T = np.eye(A.shape[1]) if Tmat is None else np.asarray(Tmat, float).copy()
    start = time.perf_counter()
    convergence = False
    W = ((A @ np.linalg.inv(T).T) ** 2 + eps) ** (p / 2 - 1)
    for it in range(1, int(maxit) + 1):
        r = GPForth(A, Tmat=T, normalize=normalize, eps=eps, maxit=gpaiter, method="lp.wls", methodArgs={"W": W})
        T_new, L = r["Th"], r["loadings"]
        W = _lp_weights(L, p, eps)
        if np.max(np.abs(L - A @ np.linalg.inv(T).T)) < eps:
            T = T_new
            convergence = True
            break
        T = T_new
    f = np.sum(np.abs(L) ** p) / L.shape[0]
    return {"loadings": L, "Phi": T.T @ T, "Th": T,
            "Table": np.array([[it, f, time.perf_counter() - start]]),
            "method": f"Lp rotation, p={p}", "orthogonal": True, "convergence": convergence, "Gq": None}


def GPFoblq_lp(A, Tmat=None, p=1, normalize=False, eps=1e-5, maxit=10000, gpaiter=5):
    """R GPFoblq.lp: oblique Lp rotation, an outer IRLS loop around GPFoblq(method='lp.wls')."""
    A = np.asarray(A, float)
    T = np.eye(A.shape[1]) if Tmat is None else np.asarray(Tmat, float).copy()
    start = time.perf_counter()
    convergence = False
    W = ((A @ np.linalg.inv(T).T) ** 2 + eps) ** (p / 2 - 1)
    for it in range(1, int(maxit) + 1):
        r = GPFoblq(A, Tmat=T, normalize=normalize, eps=eps, maxit=gpaiter, method="lp.wls", methodArgs={"W": W})
        T_new, L = r["Th"], r["loadings"]
        W = _lp_weights(L, p, eps)
        if np.max(np.abs(L - A @ np.linalg.inv(T).T)) < eps:
            T = T_new
            convergence = True
            break
        T = T_new
    f = np.sum(np.abs(L) ** p) / L.shape[0]
    return {"loadings": L, "Phi": T.T @ T, "Th": T,
            "Table": np.array([[it, f, time.perf_counter() - start]]),
            "method": f"Lp rotation, p={p}", "orthogonal": False, "convergence": convergence, "Gq": None}


def _lp_multistart(fit, A, p, eps, randomStarts, k, r):
    """The random-start outer loop of R lpT and lpQ. Keeps the lowest Lp value."""
    if randomStarts <= 1:
        return r
    n = A.shape[0]
    Qvalues = [np.sum(np.abs(r["loadings"]) ** p) / n]
    Qconv = [r["convergence"]]
    Qmin = Qvalues[0]
    for _ in range(2, randomStarts + 1):
        g = fit(Random_Start(k))
        Qval = np.sum(np.abs(g["loadings"]) ** p) / n
        Qvalues.append(Qval)
        Qconv.append(g["convergence"])
        if Qval < Qmin:
            r, Qmin = g, Qval
    Qmin = eps * np.round(Qmin / eps)
    Qvalues = eps * np.round(np.array(Qvalues) / eps)
    out = dict(r)
    out["randStartChar"] = {"randomStarts": randomStarts, "Converged": int(sum(Qconv)),
                            "atMinimum": int(np.sum(Qvalues == Qmin)), "localMins": int(len(np.unique(Qvalues)))}
    out["Qvalues"] = Qvalues
    return out


def lpT(A, Tmat=None, p=1, normalize=False, eps=1e-5, maxit=2000, randomStarts=0, gpaiter=5):
    """R lpT: orthogonal Lp rotation, with optional random starts."""
    A = np.asarray(A, float)
    k = A.shape[1]
    if randomStarts > 0:
        Tmat = Random_Start(k)
    fit = lambda T0: GPForth_lp(A, Tmat=T0, p=p, normalize=normalize, eps=eps, maxit=maxit, gpaiter=gpaiter)
    r = fit(Tmat)
    return _lp_multistart(fit, A, p, eps, randomStarts, k, r)


def lpQ(A, Tmat=None, p=1, normalize=False, eps=1e-5, maxit=2000, randomStarts=0, gpaiter=5):
    """R lpQ: oblique Lp rotation, with optional random starts."""
    A = np.asarray(A, float)
    k = A.shape[1]
    if randomStarts > 0:
        Tmat = Random_Start(k)
    fit = lambda T0: GPFoblq_lp(A, Tmat=T0, p=p, normalize=normalize, eps=eps, maxit=maxit, gpaiter=gpaiter)
    r = fit(Tmat)
    return _lp_multistart(fit, A, p, eps, randomStarts, k, r)


def Random_Start(k=2):
    """R Random.Start(k): a k x k Haar orthogonal matrix from R's seeded normal stream.

    The uniforms come from boot's R-compatible Mersenne-Twister (set.seed), and the
    normals are R's default Inversion kind: qnorm of two uniforms packed into one.
    Filling is column-major, as matrix(rnorm(k*k), k, k) does in R.
    """
    from boot import rng as _rng  # R unif_rand stream and set.seed
    from boot.series import qnorm as _qnorm  # R qnorm
    big = 134217728.0  # 2^27, R's BIG in Inversion
    def norm_rand():
        u = _rng.unif()
        u = int(big * u) + _rng.unif()
        return _qnorm(u / big)
    z = np.array([norm_rand() for _ in range(k * k)], float).reshape((k, k), order="F")
    q, r = np.linalg.qr(z)
    return q @ np.diag(np.sign(np.diag(r)))


def eiv(A, identity=None):
    A=np.asarray(A,float); k=A.shape[1]; ids=np.arange(k) if identity is None else np.asarray(identity); g=np.linalg.inv(A[ids,:]); L=np.full_like(A,np.nan); L[ids]=np.eye(k); L[np.setdiff1d(np.arange(A.shape[0]),ids)]=A[np.setdiff1d(np.arange(A.shape[0]),ids)]@g
    return {"loadings":L,"Phi":A[ids]@A[ids].T,"Th":A[ids].T,"method":"eiv","orthogonal":False,"convergence":True,"Gq":None,"Table":np.full((1,4),np.nan)}


def echelon(A, reference=None):
    A=np.asarray(A,float); k=A.shape[1]; ids=np.arange(k) if reference is None else np.asarray(reference); B=np.linalg.cholesky(A[ids]@A[ids].T); T=np.linalg.solve(A[ids],B); L=np.zeros_like(A); L[ids]=B; rest=np.setdiff1d(np.arange(A.shape[0]),ids); L[rest]=A[rest]@T
    return {"loadings":L,"Th":T,"method":"echelon","orthogonal":True,"convergence":True,"Gq":None,"Table":np.full((1,4),np.nan)}
