# locfit hat operator by probing

Pitfall seen in locfit `hatmatrix` and `lcv`.

- At a fixed bandwidth the direct fit (`ev = dat()`) is linear in `y`. The bandwidth comes from `x` alone (`nn`), so column `i` of H is the crate fit to the unit vector `e_i`. This gives H exactly, to about 1e-9 against R.
- The crate's `t0` output is not the hat diagonal. It has two columns per evaluation point. Use the probed `H_ii`.
- R's `lcv` cv term is `sum((y - (th - H_ii * (y - th)))^2)`, not the usual LOO shortcut `(y - th)/(1 - H_ii)`. The shortcut differs by about 0.14 on the verify5 inputs.
- R's `hatmatrix()` errors "data is too long" on these inputs because it uses the default tree. Compare with `t(locfit.raw(geth = 1, ev = dat()))`.
- On the default `ev = rbox()` tree, R's cv term is not the probed `H_ii`. `fitted.c` uses `inl = t0^2` at each data point, with `t0` the tree-interpolated influence plus the parametric part: `th_cv = th - inl * w * (y - th)`. The crate computes this in `cv_sum` (`fit.rs`), and `lcv` default matches R to about 1e-14.
