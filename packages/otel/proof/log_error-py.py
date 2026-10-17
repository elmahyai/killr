import statistics, time
from otel.api import *
def f(): return log_error("x")
def normalize(x):
    if x is None: return "NULL"
    if isinstance(x, bool): return "True" if x else "False"
    if isinstance(x, (str,int,float)): return str(x)
    if isinstance(x, dict): return "|".join(x.keys())
    if isinstance(x, list): return "|".join(map(str,x))
    return "Logger"
f()
t=[]
for _ in range(20):
    t0=time.perf_counter(); z=f(); t.append(time.perf_counter()-t0)
print(f"py_ms {statistics.median(t)*1000:.17g}")
print(normalize(z))
