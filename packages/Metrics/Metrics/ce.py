import numpy as np
def ce(actual, predicted):
    return float(np.mean(np.asarray(actual)!=np.asarray(predicted)))
