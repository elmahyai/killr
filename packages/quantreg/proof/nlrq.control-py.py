import statistics
import time
from quantreg import nlrq_control
z = nlrq_control()

def one():
    return [z['maxiter'], z['k'], z['InitialStepSize'], z['big'], z['eps'], z['beta']]
one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value = one()
import numpy as np
array = np.atleast_1d(np.asarray(value, dtype=float)).reshape(-1)
print(','.join(f'{item:.17g}' for item in array))
print(f'{statistics.median(elapsed):.17g}')
