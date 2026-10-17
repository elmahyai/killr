import numpy as np
def accuracy(actual, predicted):
    actual=np.asarray(actual); predicted=np.asarray(predicted)
    return float(1 - np.mean(actual != predicted))
