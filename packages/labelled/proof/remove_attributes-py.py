import json, statistics, time
from labelled import LabelledVector, remove_attributes
x=LabelledVector([1],attributes={"format.spss":"x"}); value=remove_attributes(x,["format.spss"]).attributes; t=[]
for _ in range(20):
 s=time.perf_counter(); remove_attributes(x,["format.spss"]); t.append((time.perf_counter()-s)*1000)
print(json.dumps({"value":value,"median_ms":statistics.median(t)}))
