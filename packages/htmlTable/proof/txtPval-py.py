import json, statistics, time, sys
sys.path.insert(0, "packages/htmlTable")
from htmlTable.html_table import txtPval
case=[.10234,.010234,.0010234,.000010234]; value=txtPval(case); times=[]
for _ in range(20):
 t=time.perf_counter(); txtPval(case); times.append((time.perf_counter()-t)*1000)
print(json.dumps({"value":value,"translated_ms":statistics.median(times)}))
