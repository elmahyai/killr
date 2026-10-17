import json, sys, time
sys.path.insert(0, "packages/modeltools")
from modeltools.core import *
import numpy as np
def measure(fn):
    value=fn(); times=[]
    for _ in range(20):
        t=time.perf_counter(); fn(); times.append((time.perf_counter()-t)*1000)
    return value, sorted(times)[9]
fn=lambda: infoCheck({'info': {'help': ['help']}}, 'help')
value, translated_ms=measure(fn)
print("value="+json.dumps(np.asarray(value).tolist() if hasattr(value,"tolist") else value))
print("translated_ms="+str(translated_ms))
