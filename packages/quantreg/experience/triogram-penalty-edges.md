# triogram penalty edge loop

`penalty.f` walks the triSht2tri lists, and the lists are circular. `fadjs` finds the apex on each side of an edge by walking the neighbour list of vertex i. When the partner j is the first neighbour, it is matched only on the second lap, so the walk needs about two laps of the list, not one. A tlist entry is negative on a hull edge, and the edge is kept only when the two ends are not both on the hull.

The four vertex numbers of an edge are distinct, so the `srtpai` sort is a plain ascending sort and the output order is fixed. The port keeps 1-based vertex numbers and reads slices at `k - 1`.

`interp` is not installed in the project venv. `triogram_penalty` loads its Python package from `packages/interp` and the proofs add that path to `sys.path`.
