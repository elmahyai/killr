import numpy as np
def sle(actual, predicted):
    a=np.asarray(actual,dtype=float); p=np.asarray(predicted,dtype=float)
    return (np.log1p(a)-np.log1p(p))**2
