# chull vertex order

R's `chull(x, y)` is two steps. The C routine `C_chull` (Eddy 1977) returns the hull vertex set. Then R code sorts that set by `atan2(y - cy, -(x - cx))`, where `(cx, cy)` is the mean of the set. Print `grDevices::chull` to see it.

So the output order depends on the vertex set alone. A port can copy the ordering exactly and get the set from a monotone chain on the exact coordinates.

The set is not always the strict hull. In 4000 random tie-heavy point sets, about 0.7 per cent differ from a strict monotone chain. R sometimes keeps two copies of a duplicated vertex, and sometimes keeps a collinear point on an edge. A ported `chull` must be checked against R on duplicate and collinear inputs, not only on general position points.
