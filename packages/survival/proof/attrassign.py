import statistics
import time

import numpy as np
from survival.attrassign import attrassign


class Terms:
    is_terms = True

    def __init__(self, term_labels):
        self.term_labels = list(term_labels)


class ModelMatrix:
    def __init__(self, matrix, assign):
        self.matrix = np.asarray(matrix)
        self.assign = np.asarray(assign, dtype=int)


def serialize_attrassign(aa):
    return ["|".join(aa.keys()), *[ " ".join(str(i) for i in indices) for indices in aa.values()]]


def one():
    formula_terms = Terms(["factor(ph.ecog)"])
    assign = np.array([0, 1, 1, 1], dtype=int)
    mm = ModelMatrix(np.zeros((4, 4)), assign)
    return serialize_attrassign(attrassign(mm, formula_terms))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
