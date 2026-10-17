import math, statistics, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.em_eee_ev_vvv import emEEE
n, p = 60, 3
x = np.array([[math.sin(.37*i+1.3*j)+.4*math.cos(.11*i*j)+.05*i/n*j
               for j in range(1,p+1)] for i in range(1,n+1)])
mu = np.array([[.1,.5],[-.2,.4],[.3,-.1]])
U = np.array([[1.4,.2,.1],[0,1.1,.3],[0,0,.9]])
def pars(pro, Vinv=None):
    a = {"pro": np.asarray(pro), "mean": mu,
         "variance": {"cholSigma": U, "sigma": U.T@U}}
    if Vinv is not None: a["Vinv"] = Vinv
    return a
def flat(o):
    v=o["parameters"]["variance"]
    f=lambda a: np.asarray(a).ravel(order="F").tolist()
    return [o["returnCode"]]+f(o["parameters"]["pro"])+f(o["parameters"]["mean"])+f(v["Sigma"])+f(v["cholSigma"])+f(v["sigma"])+f(o["z"])
def one():
    return [float(v) for v in flat(emEEE(x,pars([.4,.6])))+flat(emEEE(x,pars([.3,.45,.25],.15)))]
value=one(); elapsed=[]
for _ in range(20):
    t=time.perf_counter(); one(); elapsed.append((time.perf_counter()-t)*1000)
for v in value: print("%.17g"%v)
print("%.17g"%statistics.median(elapsed))
