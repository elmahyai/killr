Plot proofs: object dumps and recorder hooks

- The JSON dumps of fitted objects must carry `hypvol`. Without it, R's `predict.densityMclust` fails on `if (noise)` for a one-dimensional fit (`noise <- !is.na(object$hypvol)` gives `logical(0)`). `dump_mclust_object` and `read_mclust_object` now write and read it.
- When a plot function calls `plotDensityMclustd` inside `plot.Mclust`, the R recorder needs that function's hooks (`par` layout, diagonal `text`, panel `axis` sides, contour window). The hooks are guarded by the call stack, so other panels keep the generic recorder.
- Matplotlib does not accept X11 names such as `grey30`. Use the hex value R gives (`gray(0.3)` is `#4D4D4D`).
- Python proof execution requires the prebuilt `mclust_kernels` extension; without it, importing the package fails before the plot module can run.
- For plot proofs, match R's `expand.grid` ordering (the first dimension varies fastest) and include all covariance fields consumed by the density dispatcher.
