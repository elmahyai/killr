from .precision import precision
from .recall import recall
def fbeta_score(actual, predicted, beta=1):
    prec=precision(actual,predicted); rec=recall(actual,predicted)
    return (1+beta**2)*prec*rec/(beta**2*prec+rec)
