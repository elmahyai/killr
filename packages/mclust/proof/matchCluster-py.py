import statistics,sys,time
sys.path.insert(0,"/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.match_cluster import matchCluster
def one(): return matchCluster(["A","A","B","B","B"],[1,1,2,1,2])
value=one();elapsed=[]
for _ in range(20):
 t=time.perf_counter();one();elapsed.append((time.perf_counter()-t)*1000)
for x in value["cluster"]: print(x)
for x in value["misclassified"]: print(int(x))
for x in value["ord"]: print(x)
print("%.17g"%statistics.median(elapsed))
