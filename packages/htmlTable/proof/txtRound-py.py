import json, statistics, time, sys
sys.path.insert(0, "packages/htmlTable")
from htmlTable.html_table import txtRound
case=[1.023,3.14159,None]; value=txtRound(case,digits=1); times=[]
for _ in range(20):
 t=time.perf_counter(); txtRound(case,digits=1); times.append((time.perf_counter()-t)*1000)
print(json.dumps({"value":value,"translated_ms":statistics.median(times)}))
