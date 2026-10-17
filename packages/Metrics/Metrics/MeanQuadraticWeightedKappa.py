import numpy as np
def MeanQuadraticWeightedKappa(kappas, weights=None):
    k=np.asarray(kappas,dtype=float)
    w=np.ones(len(k)) if weights is None else np.asarray(weights,dtype=float)
    w=w/np.mean(w); k=np.sign(k)*np.minimum(.999,np.abs(k)); k=np.sign(k)*np.maximum(.001,np.abs(k))
    z=.5*np.log((1+k)/(1-k)); z=np.mean(z*w)
    return float((np.exp(2*z)-1)/(np.exp(2*z)+1))
