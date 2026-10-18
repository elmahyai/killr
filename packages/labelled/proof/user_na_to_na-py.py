import json, statistics, time
from labelled import LabelledVector, user_na_to_na
x=LabelledVector([1,9],na_values=[9]); value=user_na_to_na(x).values; t=[]
for _ in range(20):
 s=time.perf_counter(); user_na_to_na(x); t.append((time.perf_counter()-s)*1000)
print(json.dumps({"value":value,"median_ms":statistics.median(t)}))
