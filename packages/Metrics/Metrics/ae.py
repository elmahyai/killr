import numpy as np
def ae(actual, predicted):
    return np.abs(np.asarray(actual, dtype=float)-np.asarray(predicted, dtype=float))
