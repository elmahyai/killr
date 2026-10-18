import json, statistics, time
from labelled import LabelledVector, na_values
x=LabelledVector([1,9],na_values=[9]); value=na_values(x); t=[]
for _ in range(20):
 s=time.perf_counter(); na_values(x); t.append((time.perf_counter()-s)*1000)
print(json.dumps({"value":value,"median_ms":statistics.median(t)}))
