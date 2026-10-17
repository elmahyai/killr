import numpy as np
def se(actual, predicted):
    x=np.asarray(actual,dtype=float)-np.asarray(predicted,dtype=float)
    return x*x
