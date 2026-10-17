# predict.qss2 and plot.qss2 lessons

- `predict.qss2` takes the x and y names from `dimnames(object)[[2]]`. A NumPy array has none, so `predict_qss2` takes `fnames`. Without dimnames R fails on the list branch, so the R proof sets `c("x", "y", "zfit")` as `predict.rqss` does.
- The hull test is `in.convex.hull` with `strict = TRUE`. A newdata point on the outer hull, such as a design vertex that is on the hull, stops with "some newdata points outside convex hull". Proofs use interior points, for example midpoints of interior design points.
- `plot.qss2` with the default `render = "contour"` plots the points with `type = "n"` and labels `x` and `y`. It contours `interp::interp` on its default 40 by 40 grid, then returns `convex.hull(plot.it = TRUE)`. That returns `invisible(list(x, y, i))`, and `plot.qss2` returns it. The Python port checks the grid, window, and hull. Contour lines and levels are Matplotlib's.
- `render = "persp"` returns R's graphics viewing matrix and is not translated. `render = "rgl"` needs rgl, which is not installed and is routed to Plotly.
- The R reference for `predict.qss2` builds `matrix.csr` objects from SparseM, which quantreg lists under `Depends`. SparseM is not in `registry.json`.
