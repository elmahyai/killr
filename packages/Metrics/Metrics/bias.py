import numpy as np
def bias(actual, predicted):
    return float(np.mean(np.asarray(actual,dtype=float)-np.asarray(predicted,dtype=float)))
