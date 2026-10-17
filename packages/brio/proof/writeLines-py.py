import json,statistics,tempfile,time,sys
sys.path.insert(0,str(__file__).split("/packages/")[0]+"/packages/brio")
from brio import writeLines
with tempfile.NamedTemporaryFile() as f:
 one=lambda:(writeLines(["a\r\nb",""],f.name,sep="\r\n"),open(f.name,"rb").read());value=one();times=[]
 for _ in range(20):
  t=time.perf_counter();one();times.append((time.perf_counter()-t)*1000)
 print(json.dumps({"value":list(value[1]),"median_ms":statistics.median(times)}))
