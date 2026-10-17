# tri.mesh is the sweep hull, not tripack

interp's `tri.mesh` does not call tripack. Its triangulation is the s-hull sweep of David Sinclair, C++ in `src/s_hull_pro.cpp`, called from `shull.deltri`. The triangle list, neighbours, arcs, and convex hull order all come from that sweep. Read `src/shullDeltri.cpp` before assuming a Delaunay routine from another library gives the same output.

Two facts decide the port:

- The sweep stores coordinates as float32 (`Shx` fields are `float`). The circumcircle table is also float32 (`CC`). A double-precision port differs in the last digits of `cclist`, and it can change the triangulation on near-degenerate input.
- `scipy.spatial.Delaunay` matches the canonical triangles on random sets, but not on a 5 by 5 grid, where four points are co-circular. It also gives no `trlist` order, neighbour columns, arc order, or hull order. The kernel was vendored and compiled unchanged, in `crates/interp`, so the output is the same integers as R.

Checked against interp 1.1-6: 7 proof cases plus 30 random sets with 5 to 150 points. Triangles, `cclist`, arcs, and hull order match R exactly.
