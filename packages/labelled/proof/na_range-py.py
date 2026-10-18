import json, statistics, time
from labelled import LabelledVector, na_range
x=LabelledVector([1,2],na_range=[2,9]); value=na_range(x); t=[]
for _ in range(20):
 s=time.perf_counter(); na_range(x); t.append((time.perf_counter()-s)*1000)
print(json.dumps({"value":value,"median_ms":statistics.median(t)}))
