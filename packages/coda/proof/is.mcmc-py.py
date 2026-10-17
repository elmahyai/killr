import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.as_mcmc import Mcmc, as_mcmc
from coda.is_mcmc import is_mcmc
from coda.mcmc_list import mcmc_list

root = Path(__file__).resolve().parent
package = root.parent


def _word(flag):
    return "TRUE" if flag else "FALSE"


def one():
    n = 2000
    i = np.arange(1, n + 1, dtype=np.float64)
    x = np.column_stack(
        (
            np.sin(i / 3) + 0.2 * np.cos(i),
            np.cos(i / 5) + 0.01 * i,
            np.full(n, 2.0),
        )
    )
    chain = as_mcmc(x)
    vector = as_mcmc(np.sin(i / 7))
    chains = mcmc_list(chain, as_mcmc(x))
    obsolete = Mcmc(data=np.arange(1, 25, dtype=np.float64).reshape(2, 3, 4))
    try:
        is_mcmc(obsolete)
        msg = ""
    except ValueError as exc:
        msg = str(exc)
    flags = [
        1.0 if is_mcmc(chain) else 0.0,
        1.0 if is_mcmc(vector) else 0.0,
        1.0 if is_mcmc(x) else 0.0,
        1.0 if is_mcmc(chains) else 0.0,
        1.0 if is_mcmc(None) else 0.0,
        1.0 if is_mcmc([chain]) else 0.0,
    ]
    coded = [float(len(msg))]
    coded.extend(float(ord(char)) for char in msg)
    return flags + coded


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

(root / "is.mcmc-py.txt").write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)

n = 2000
i = np.arange(1, n + 1, dtype=np.float64)
x = np.column_stack(
    (
        np.sin(i / 3) + 0.2 * np.cos(i),
        np.cos(i / 5) + 0.01 * i,
        np.full(n, 2.0),
    )
)
chain = as_mcmc(x)
vector = as_mcmc(np.sin(i / 7))
chains = mcmc_list(chain, as_mcmc(x))
try:
    is_mcmc(Mcmc(data=np.arange(1, 25, dtype=np.float64).reshape(2, 3, 4)))
    msg = ""
except ValueError as exc:
    msg = str(exc)

example = (
    f"mcmc matrix: {_word(is_mcmc(chain))}\n"
    f"mcmc vector: {_word(is_mcmc(vector))}\n"
    f"numeric matrix: {_word(is_mcmc(x))}\n"
    f"mcmc.list: {_word(is_mcmc(chains))}\n"
    f"NULL: {_word(is_mcmc(None))}\n"
    f"list: {_word(is_mcmc([chain]))}\n"
    f"{msg}\n"
)
(package / "docs" / "output" / "is.mcmc-python.txt").write_text(example)
