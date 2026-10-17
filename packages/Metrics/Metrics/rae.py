import numpy as np
from .ae import ae
def rae(actual, predicted):
    a=np.asarray(actual,dtype=float)
    return float(np.sum(ae(predicted,a))/np.sum(ae(a,np.mean(a))))
