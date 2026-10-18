import json, statistics, time
from labelled import LabelledVector, remove_val_labels
x=LabelledVector([1],{"one":1}); value=remove_val_labels(x).labels; t=[]
for _ in range(20):
 s=time.perf_counter(); remove_val_labels(x); t.append((time.perf_counter()-s)*1000)
print(json.dumps({"value":value,"median_ms":statistics.median(t)}))
