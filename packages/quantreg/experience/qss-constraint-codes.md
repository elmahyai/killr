# qss constraint letters and binding data

In R's `qss1`, `constraint = "C"` is concave (`R <- -A`) and `"V"` is convex (`R <- A`). The reverse is easy to assume. Check a `C` or `V` proof by its sign, not its name.

A monotone or shape check needs data where the unconstrained fit breaks the shape. On `y = sin(x) + 0.5 z + 0.3 sin(7i)` with `x = 2 sin(i)`, the unconstrained slopes are all positive, so `I` returns the unconstrained fit and proves nothing. Adding `-0.4 x` to `y` makes `I` and `C` bind.
