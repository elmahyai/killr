import json, statistics, time
from labelled import LabelledVector, set_na_values
x=LabelledVector([1,2]); value=set_na_values(x, _values=[2]); t=[]
for _ in range(20):
 s=time.perf_counter(); set_na_values(x, _values=[2]); t.append((time.perf_counter()-s)*1000)
print(json.dumps({"value":value.na_values,"median_ms":statistics.median(t)}))
