import numpy as np
from .ae import ae
def mase(actual, predicted, step_size=1):
    a=np.asarray(actual,dtype=float); p=np.asarray(predicted,dtype=float); n=len(a); end=n-step_size
    return float(np.sum(ae(a,p))/(n*np.sum(ae(a[step_size:],a[:end]))/end))
