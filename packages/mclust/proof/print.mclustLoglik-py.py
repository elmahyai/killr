import importlib.util, statistics, time
from pathlib import Path
spec=importlib.util.spec_from_file_location("m",Path(__file__).parents[1]/"mclust"/"print_summary.py"); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
x={"value":-12.3,"df":5,"nobs":10}
one=lambda:m.print_mclust_loglik(x); value=one(); t=[]
for _ in range(20):
 a=time.perf_counter(); one(); t.append((time.perf_counter()-a)*1000)
print(value); print(f"{statistics.median(t):.17g}")
