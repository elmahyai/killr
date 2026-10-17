import numpy as np
def ll(actual, predicted):
    a=np.asarray(actual,dtype=float); p=np.asarray(predicted,dtype=float)
    with np.errstate(divide="ignore",invalid="ignore"):
        score=-(a*np.log(p)+(1-a)*np.log(1-p))
    score=np.asarray(score)
    score[a==p]=0
    score[np.isnan(score)]=np.inf
    return score
