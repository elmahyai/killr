EDDA factor levels and model search

- R `as.factor` sorts the levels. `_mclust_mutils.as_factor` keeps first-appearance order, so `mclust_da` now uses `_r_factor` (sorted; numeric labels in numeric order). Unsorted data gives a different class order if `as_factor` is used.
- R EDDA search: one M-step per name in the union of the per-class names, on `z = unmap(class)` with G = number of classes. BIC uses `equalPro = TRUE`. The kept model is the last one at the running maximum. Each class then takes its slice with `pro = 1` and `G = 1`.
- In `mclust_dr(object, ...)`, the parameter `object` shadows the built-in. `dtype=object` passes the dict to numpy and fails with "entry not a 2- or 3- tuple". Use `np.object_`.
- Run the Python proofs with `../../.venv/bin/python3` from `packages/mclust`. `mclust_kernels` is installed only in the venv.
