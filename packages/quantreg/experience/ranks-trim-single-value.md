# ranks() trim with one value does nothing

R's `ranks(v, score = "wilcoxon", trim = t)` with a single `trim` value expands it to `c(t, 1 - t)`, but the trimming block is the `else` of that test. So one value leaves the process untrimmed and `A2` stays `1/12`. Only two values trim the process, and `ranks` in `quantreg/process.py` follows that. Proofs for trimming must pass `trim = c(lo, hi)`, or they compare against the untrimmed ranks and fail.
