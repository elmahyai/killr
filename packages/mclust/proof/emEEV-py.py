import math, statistics, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.em_eee_ev_vvv import emEEV
n,p=60,3
x=np.array([[math.sin(.37*i+1.3*j)+.4*math.cos(.11*i*j)+.05*i/n*j for j in range(1,p+1)] for i in range(1,n+1)])
mu=np.array([[.1,.5],[-.2,.4],[.3,-.1]])
a,b=math.pi/6,math.pi/5
Rz=np.array([[math.cos(a),-math.sin(a),0],[math.sin(a),math.cos(a),0],[0,0,1]])
Rx=np.array([[1,0,0],[0,math.cos(b),-math.sin(b)],[0,math.sin(b),math.cos(b)]])
O=Rz@Rx; O3=np.repeat(O[:,:,None],2,axis=2); shape=np.array([[1.5,.8],[.6,1.4],[.9,1.1]])
def pars(pro,Vinv=None):
    q={"pro":np.asarray(pro),"mean":mu,"variance":{"scale":.9,"shape":shape,"orientation":O3}}
    if Vinv is not None:q["Vinv"]=Vinv
    return q
def flat(o):
    v=o["parameters"]["variance"]; f=lambda a:np.asarray(a).ravel(order="F").tolist()
    return [o["returnCode"]]+f(o["parameters"]["pro"])+f(o["parameters"]["mean"])+[v["scale"]]+f(v["shape"])+f(v["orientation"])+f(v["sigma"])+f(o["z"])
def one():return [float(v) for v in flat(emEEV(x,pars([.4,.6])))+flat(emEEV(x,pars([.3,.45,.25],.15)))]
value=one();elapsed=[]
for _ in range(20):
    t=time.perf_counter();one();elapsed.append((time.perf_counter()-t)*1000)
for v in value:print("%.17g"%v)
print("%.17g"%statistics.median(elapsed))
