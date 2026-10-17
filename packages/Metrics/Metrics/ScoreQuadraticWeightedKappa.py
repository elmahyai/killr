import numpy as np
def ScoreQuadraticWeightedKappa(rater_a, rater_b, min_rating=None, max_rating=None):
    a=np.asarray(rater_a); b=np.asarray(rater_b)
    lo=int(np.min(np.r_[a,b])) if min_rating is None else int(min_rating); hi=int(np.max(np.r_[a,b])) if max_rating is None else int(max_rating)
    labels=np.arange(lo,hi+1); n=len(a)
    conf=np.zeros((len(labels),len(labels)))
    for x,y in zip(a,b): conf[x-lo,y-lo]+=1
    conf/=n
    ha=np.array([np.sum(a==x) for x in labels],dtype=float)/len(labels)
    hb=np.array([np.sum(b==x) for x in labels],dtype=float)/len(labels)
    exp=np.outer(ha,hb); exp/=np.sum(exp)
    weights=(labels[:,None]-labels[None,:])**2
    return float(1-np.sum(weights*conf)/np.sum(weights*exp))
