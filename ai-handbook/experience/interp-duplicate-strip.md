# interp duplicate = "strip" keeps the first point

In interp 1.1-6, `interp(duplicate = "strip")` keeps the first occurrence of each repeated (x, y) and drops the later copies. The code is `z <- z[ord]` with `ord <- !duplicated(xy)` in R/interp.R.

`tri.mesh(duplicate = "strip")` is different. It drops every point that is repeated, so a point that appears twice is removed entirely. The code is `hist(i, ...)$counts == 1` in R/tri.mesh.R.

Do not share one port of "strip" between the two. A port for `interp` must keep the first occurrence, and a port for `tri.mesh` must drop all repeats.

Checked against interp 1.1-6: the `dups-strip` case in the interp proof matches R at 0.
