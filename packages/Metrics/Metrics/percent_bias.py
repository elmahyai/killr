import numpy as np
def percent_bias(actual, predicted):
    a=np.asarray(actual,dtype=float); p=np.asarray(predicted,dtype=float)
    with np.errstate(divide="ignore",invalid="ignore"):
        return float(np.mean((a-p)/np.abs(a)))
