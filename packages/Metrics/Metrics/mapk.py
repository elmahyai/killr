import numpy as np
from .apk import apk
def mapk(k, actual, predicted):
    if len(actual)==0 or len(predicted)==0: return 0.0
    if not isinstance(actual,list): actual=[actual]
    if not isinstance(predicted,list): predicted=[predicted]
    return float(np.mean([apk(k,a,p) for a,p in zip(actual,predicted)]))
