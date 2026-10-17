import numpy as np
def recall(actual, predicted):
    a=np.asarray(actual); p=np.asarray(predicted)
    return float(np.mean(p[a==1]))
