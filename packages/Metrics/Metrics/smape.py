import numpy as np
from .ae import ae
def smape(actual, predicted):
    a=np.asarray(actual,dtype=float); p=np.asarray(predicted,dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return float(2*np.mean(ae(a,p)/(np.abs(a)+np.abs(p))))
