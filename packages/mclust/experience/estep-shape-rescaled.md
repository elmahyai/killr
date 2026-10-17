`dens` for the diagonal-shape models EEI, VEI, EVI and VVI rescales the caller's `parameters["variance"]["shape"]` in place. After one call, `shape` holds different numbers from the ones it held before (for example [9.886, 0.0047, 21.53] becomes [0.1319, 0.00288, 0.1947] on the case D class of 3 points), so a later `dens`, `predict.MclustDA` or `logLik.MclustDA` on the same object gives different results. R does not do this, because `.Fortran` copies its arguments.

The cause is `_estep_es` in `mclust/_mclust_em_for_ssc.py` (loaded by `loglik_mclust._load_em`). For the EEI, VEI, EVI and VVI branches it passes `np.asarray(var["shape"], dtype=float)` straight to the ctypes pointer, so no copy is made and the Fortran routine writes into the caller's array. The `scale` and `sigmasq` branches have the same pattern.

Found in the MclustDA default-modelType proof: `MclustDA(x, y)` on case D (a class of 3 points, EEI, G = 2) fitted correctly, but its `shape` changed as soon as `logLik.MclustDA` ran, and the training predictions of `predict.MclustDA` then differed from R. Copying the parameters before each `dens` call (for the scratch check only) removed the difference, giving a maximum of 1.7e-13 on that case.

Fix in the owning module: copy the arrays before they reach the pointer (`np.array(var["shape"], dtype=float, copy=True)`, and the same for `scale` and `sigmasq`).
