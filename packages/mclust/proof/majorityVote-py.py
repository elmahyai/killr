import statistics,sys,time
sys.path.insert(0,"/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.majority_vote import majorityVote
def one(): return majorityVote(["a","b","a","c","a"])
value=one();elapsed=[]
for _ in range(20):
 t=time.perf_counter();one();elapsed.append((time.perf_counter()-t)*1000)
print(value["ind"]);print(value["majority"])
for x in value["table"].values(): print(x)
print("%.17g"%statistics.median(elapsed))
