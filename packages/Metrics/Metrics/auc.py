import numpy as np
def auc(actual, predicted):
    a=np.asarray(actual); p=np.asarray(predicted,dtype=float)
    order=np.argsort(p,kind="mergesort"); ranks=np.empty(len(p),dtype=float)
    i=0
    while i<len(p):
        j=i+1
        while j<len(p) and p[order[j]]==p[order[i]]: j+=1
        ranks[order[i:j]]=(i+1+j)/2
        i=j
    npos=float(np.sum(a==1)); nneg=len(a)-npos
    return float((np.sum(ranks[a==1])-npos*(npos+1)/2)/(npos*nneg))
