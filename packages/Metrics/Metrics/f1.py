def f1(actual, predicted):
    act=list(dict.fromkeys(actual)); pred=list(dict.fromkeys(predicted))
    aset=set(act); pset=set(pred); tp=len(aset&pset); fp=len(pset-aset); fn=len(aset-pset)
    if tp==0: return 0
    precision=tp/(tp+fp); recall=tp/(tp+fn)
    return 2*precision*recall/(precision+recall)
