The earlier named gap for `MclustBootstrap` no longer holds for the default
`type = "bs"`. Its resampling uses `boot.rng.sample_int` (R's Rejection
`sample.int`), and each refit calls `me` on the resampled `data` and `z`. With
`set.seed` on both sides, seeds 42 and 2026 match R with a maximum difference of
0 over 126,007 values, including a run with 2 non-fits
(`packages/mclust/proof/MclustBootstrap-py.py`). Resamples contain duplicate
rows, and this path is not affected: `me` does not run the `dupPartition` step
that is still open in `Mclust`. `wlbs`, `pb` and `jk` are in
`bootstrap_family.py` too. `wlbs` draws its Gamma weights with R's `rgamma`
(nmath), loaded from `extradistr._rgen`; under `set.seed` it matches R to
about 1e-16 for shape 1. `jk` does not decrement `b` on a failed refit, and
its `max.nonfit` default is `10 * n`, because R reads that default after
`nboot <- n`.

For `mclustBootstrapLRT`, the ported `norm_rand` (Inversion) and `unif_rand`
match R's `rnorm` and `runif` under `set.seed` within 1e-8. The check was
10,000 draws each for seeds 42, 1, and 2026, with a maximum difference of
8.9e-16 (`packages/mclust/proof/mclustBootstrapLRT-rng-compare.py`). The
RNG is not a blocker. `mclustBootstrapLRT` is translated
(`mclust/mclust_bootstrap_lrt.py`): with the same seed, the default call and a
`nboot = 15, maxG = 2` call match R within 1.2e-13
(`packages/mclust/proof/mclustBootstrapLRT-compare.py`). The `mclustBIC` path
for EEE with G = 1:9 also matches R within 8.5e-14.
