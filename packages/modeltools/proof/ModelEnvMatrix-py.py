import json, sys, time
sys.path.insert(0, "packages/modeltools")
from modeltools.core import *
import numpy as np
def measure(fn):
    value=fn(); times=[]
    for _ in range(20):
        t=time.perf_counter(); fn(); times.append((time.perf_counter()-t)*1000)
    return value, sorted(times)[9]
e=ModelEnvMatrix(np.array([[1,4],[2,5],[3,6]]), np.array([[7],[8],[9]])); fn=lambda: np.r_[e.get('designMatrix').ravel(order='F'), e.get('responseMatrix').ravel(order='F')]
value, translated_ms=measure(fn)
print("value="+json.dumps(np.asarray(value).tolist() if hasattr(value,"tolist") else value))
print("translated_ms="+str(translated_ms))
