import time, json, pathlib, sys
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from viridisLite.palettes import *
fs=['cividis','inferno','magma','mako','plasma','rocket','turbo','viridis']
for f in fs:
 fn=globals()[f]; fn(1); ts=[]
 for _ in range(20):
  a=time.perf_counter(); z=fn(1); ts.append((time.perf_counter()-a)*1000)
 print(f,'|',','.join(z.tolist()),'|',float(np.median(ts)))
a=time.perf_counter();z=viridisMap(1);unt=(time.perf_counter()-a)*1000;ts=[]
for _ in range(20):
 a=time.perf_counter();z=viridisMap(1);ts.append((time.perf_counter()-a)*1000)
print('viridisMap','|',','.join(str(x) for k in ['R','G','B','alpha'] for x in z[k]),'|',float(np.median(ts)))
