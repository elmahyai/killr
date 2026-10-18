# R lazy arguments make timing stubs measure nothing

A proof that swaps R's drawing calls for a no-op recorder can time almost nothing. R passes arguments as promises, and a function that never reads them never evaluates them. In hexbin, `hexpolygon()` with `grid.polygon()` and `polygon()` replaced by no-ops timed at about 36 microseconds for 2000 points, because the `unit()` and `rep.int()` vectors were never built.

Fix: in the no-op recorder, call `force()` on every argument the real function computes, for example `force(x); force(y); force(id.lengths)`. Then the timing includes building those vectors, as the real call does. Check that a timing is plausible for the input size before recording it.
