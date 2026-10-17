import numpy as np
def precision(actual, predicted):
    a=np.asarray(actual); p=np.asarray(predicted)
    return float(np.mean(a[p==1]))
