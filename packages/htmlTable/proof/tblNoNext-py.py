import json, statistics, time, sys
sys.path.insert(0, "packages/htmlTable")
from htmlTable.html_table import tblNoNext
value=tblNoNext(table_counter=4); times=[]
for _ in range(20):
 t=time.perf_counter(); tblNoNext(table_counter=4); times.append((time.perf_counter()-t)*1000)
print(json.dumps({"value":value,"translated_ms":statistics.median(times)}))
