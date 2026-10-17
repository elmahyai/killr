# Subset selection needs multi-component fits

`MclustDRsubsel` on a `Mclust`-type `MclustDR` object is not a single-component job. Each cycle of `MclustDRsubsel1cycle` calls `mclustBIC` with the requested `G` (the proof uses `1:3`, and the default is `1:9`), and the bic.diff rows take the best `G` from those tables. `MclustDRsubsel_cluster` then refits with `Mclust(G = G)` on the selected directions.

The gate is cleared for the `Mclust` path. The Python port uses `mclustBIC` in `mclust_dr_subsel1cycle.py`, `Mclust` in `mclust_dr_subsel_cluster.py`, and `MclustDRBICreg` in `mclust_dr_bicreg.py`. It runs with `hcUse = "VARS"`, as R sets it. On the banknote chain (`Mclust(G = 3, VEI)`, then `MclustDR(lambda = 0.7)`), `MclustDRsubsel` and `summary.MclustDRsubsel` match R within 1e-8 for `G = 1:3` and for the default `G = 1:9`.

Still open: the EDDA/MclustDA classification path (`mclust_dr_subsel_classif.py`) still shells out through `_mclust_dr_subsel_rfit.py`. The translated `MclustDA` fits only the first name in `modelNames`, while R searches all of them, and it returns `bic = None`, while R uses `2 * loglik - log(n) * df`.
