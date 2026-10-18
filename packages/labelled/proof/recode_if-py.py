import json, statistics, time
from labelled import LabelledVector, recode_if
x=LabelledVector([1,2,3]); value=recode_if(x,[False,True,False],[9]).values; t=[]
for _ in range(20):
 s=time.perf_counter(); recode_if(x,[False,True,False],[9]); t.append((time.perf_counter()-s)*1000)
print(json.dumps({"value":value,"median_ms":statistics.median(t)}))
