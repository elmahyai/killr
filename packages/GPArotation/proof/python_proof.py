import sys,time,numpy as np,csv
sys.path.insert(0,'packages/GPArotation')
import GPArotation as g
A=np.array([[.8,.1,.2],[.2,.7,.1],[.1,.2,.9],[.6,.2,.3],[.2,.8,.4]],float)
Target=np.zeros_like(A)
W=np.ones_like(A)
cases={
 'oblimin':lambda:g.oblimin(A,maxit=200),'quartimax':lambda:g.quartimax(A,maxit=200),
 'GPFRSoblq':lambda:g.GPFRSoblq(A,maxit=200),'GPFRSorth':lambda:g.GPFRSorth(A,maxit=200),
 'GPFoblq.lp':lambda:g.GPFoblq_lp(A,maxit=200),'GPForth.lp':lambda:g.GPForth_lp(A,maxit=200),
 'bentlerT':lambda:g.bentlerT(A,maxit=200),'bentlerQ':lambda:g.bentlerQ(A,maxit=200),
 'tandemI':lambda:g.tandemI(A,maxit=200),'tandemII':lambda:g.tandemII(A,maxit=200),
 'bigeominT':lambda:g.bigeominT(A,maxit=200),'bigeominQ':lambda:g.bigeominQ(A,maxit=200),
 'infomaxT':lambda:g.infomaxT(A,maxit=200),'infomaxQ':lambda:g.infomaxQ(A,maxit=200),
 'mccammon':lambda:g.mccammon(A,maxit=200),'bifactorT':lambda:g.bifactorT(A,maxit=200),
 'bifactorQ':lambda:g.bifactorQ(A,maxit=200),'equamax':lambda:g.equamax(A,maxit=200),
 'parsimax':lambda:g.parsimax(A,maxit=200),'varimin':lambda:g.varimin(A,maxit=200),
 'lpT':lambda:g.lpT(A,maxit=200),'lpQ':lambda:g.lpQ(A,maxit=200),
 'targetT':lambda:g.targetT(A,Target=Target,maxit=200),'targetQ':lambda:g.targetQ(A,Target=Target,maxit=200),
 'pstT':lambda:g.pstT(A,W=W,Target=Target,maxit=200),'pstQ':lambda:g.pstQ(A,W=W,Target=Target,maxit=200),
 'oblimax':lambda:g.oblimax(A,maxit=200),'binormamin':lambda:g.binormamin(A,maxit=200),
 'entropy':lambda:g.entropy(A,maxit=200),'simplimax':lambda:g.simplimax(A,maxit=200)}
rvals={r[0]:np.array([float(x) if x != "NA" else np.nan for x in r[1:]]) for r in csv.reader(open('packages/GPArotation/docs/output/r_values.csv'))}
for name,fn in cases.items():
 result=fn(); ts=[]
 for _ in range(20):
  t=time.perf_counter(); fn(); ts.append((time.perf_counter()-t)*1000)
 pv=np.r_[result['loadings'].ravel(order='F'),result['Table'][-1,1]]
 d=np.abs(pv-rvals[name]); d=d[np.isfinite(d)]
 print(name, f'max_abs_diff={np.max(d) if len(d) else 0:.3e} python_ms={np.median(ts):.6f}')
