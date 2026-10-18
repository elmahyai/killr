import json, statistics, time, sys
sys.path.insert(0, "packages/htmlTable")
from htmlTable.html_table import txtInt
case=[123,12345,None]; value=txtInt(case); times=[]
for _ in range(20):
 t=time.perf_counter(); txtInt(case); times.append((time.perf_counter()-t)*1000)
print(json.dumps({"value":value,"translated_ms":statistics.median(times)}))
