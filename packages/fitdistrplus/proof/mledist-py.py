import time, numpy as np
from _batch_fixture import run
t0=time.perf_counter(); value=run("mledist"); once=time.perf_counter()-t0
times=[]
for _ in range(20):
    t0=time.perf_counter(); run("mledist"); times.append(time.perf_counter()-t0)
print({"value": value["estimate"].tolist(), "once_ms": once*1000, "translated_ms": np.median(times)*1000})
