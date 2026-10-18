# quantmod stub reference

The R library at `~/R/x86_64-pc-linux-gnu-library/4.5` holds a local stand-in for quantmod 0.4.29 ("A local stand-in. getSymbols is not implemented."). Its `getSymbols` stops with `quantmod is not translated`. No quantmod tarball is under `cran/contrib`.

What this means for proofs:

- An R reference that calls `quantmod::getSymbols`, such as tseries `get.hist.quote`, fails before any download. The R proof records `status: blocked`, and the cause is the stub, not the network.
- Do not treat a Python port's output as a match. There is no real R output to compare with.
- The stub error is not a network error, so do not spend the 30-second network retries on it.

Checked on 2026-10-17 for tseries `get.hist.quote`.
