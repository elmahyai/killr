import json, sys, time
sys.path.insert(0, "packages/modeltools")
from modeltools.core import *
import numpy as np
def measure(fn):
    value=fn(); times=[]
    for _ in range(20):
        t=time.perf_counter(); fn(); times.append((time.perf_counter()-t)*1000)
    return value, sorted(times)[9]
e=ModelEnvFormula('y ~ x', {'y':[1.,2.,3.], 'x':[2.,4.,6.]}); fn=lambda: np.r_[e.get('designMatrix').ravel(order='F'), e.get('responseMatrix').ravel(order='F')]
value, translated_ms=measure(fn)
print("value="+json.dumps(np.asarray(value).tolist() if hasattr(value,"tolist") else value))
print("translated_ms="+str(translated_ms))
