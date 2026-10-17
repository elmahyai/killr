# Weighted EM takes one M-step per pass

`me.weighted` (R `weights.R`) runs an outer loop. Each pass calls `mstep` once on the weighted responsibilities `z * weights`, then divides `pro` by `mean(weights)`, then calls `estep`, then `dens` for the weighted log-likelihood. Do not swap the single `mstep` for `meE`. `meE` runs the whole inner EM to convergence, so the outer loop reaches a different fixed point. For the one-dimensional E model on `x = 1:4` with the fixed `z`, that gave a loglik gap of 2.4e-6 against R. Using `mstep`, `estep`, and `dens` gives a max difference of 0.0.

BIC uses `nMclustParams(modelName, d, G)` from R, not a constant. For E, d = 1, G = 2 that is 4. The old constant 3 gave a wrong BIC.

With that loop, all 16 models that R's `mstep`, `estep`, and `dens` accept match R within 1e-8 for unit and non-unit weights (E and V on one-dimensional data, the other 14 on two-dimensional data with G = 3). Worst difference was about 1e-13. Run `.venv/bin/python proof/me.weighted-compare.py` from `packages/mclust`. The plain `python3` lacks `mclust_kernels`.
