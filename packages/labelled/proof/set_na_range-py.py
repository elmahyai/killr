import json, statistics, time
from labelled import LabelledVector, set_na_range
x=LabelledVector([1,2]); value=set_na_range(x, _values=[2,9]); t=[]
for _ in range(20):
 s=time.perf_counter(); set_na_range(x, _values=[2,9]); t.append((time.perf_counter()-s)*1000)
print(json.dumps({"value":value.na_range,"median_ms":statistics.median(t)}))
