import json,statistics,tempfile,time,sys
sys.path.insert(0,str(__file__).split("/packages/")[0]+"/packages/brio")
from brio import read_file_raw
with tempfile.NamedTemporaryFile() as f:
 f.write(bytes([0,1,255,10]));f.flush();one=lambda:read_file_raw(f.name);value=one();times=[]
 for _ in range(20):
  t=time.perf_counter();one();times.append((time.perf_counter()-t)*1000)
 print(json.dumps({"value":list(value),"median_ms":statistics.median(times)}))
