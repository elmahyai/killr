# Constraint duals have no upper bound 1

`srqfn` holds each dual slack in a box `0 <= x <= u` with `u = 1`, because the rq dual is `a` in `[0, 1]`. The constraint rows `R b >= r` add duals `c >= 0` with no upper bound, so `srqfn` cannot hold them. Calling `srqfn` on a design with the constraint rows stacked in would cap the multipliers at 1 and return a wrong fit. `rq.fit.sfnc` needs `srqfnc`, which keeps `x2 >= 0` with no `s`, `u` bound, as `crates/quantreg_sfnc` does.
