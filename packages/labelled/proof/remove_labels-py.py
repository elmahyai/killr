import json, statistics, time
from labelled import LabelledVector, remove_labels
x=LabelledVector([1],{"one":1},"q",[9]); value=remove_labels(x).label; t=[]
for _ in range(20):
 s=time.perf_counter(); remove_labels(x); t.append((time.perf_counter()-s)*1000)
print(json.dumps({"value":value,"median_ms":statistics.median(t)}))
