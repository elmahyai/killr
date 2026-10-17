def apk(k, actual, predicted):
    score=0.0; cnt=0.0; actual_set=set(actual); seen=set()
    for i,item in enumerate(predicted[:min(k,len(predicted))],1):
        if item in actual_set and item not in seen:
            seen.add(item); cnt+=1; score+=cnt/i
    return score/min(len(actual),k)
