import json, statistics, time
from labelled import LabelledVector, remove_var_label
x=LabelledVector([1],label="q"); value=remove_var_label(x).label; t=[]
for _ in range(20):
 s=time.perf_counter(); remove_var_label(x); t.append((time.perf_counter()-s)*1000)
print(json.dumps({"value":value,"median_ms":statistics.median(t)}))
