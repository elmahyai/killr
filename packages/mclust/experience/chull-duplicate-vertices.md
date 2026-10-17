R's `chull` (C routine, Eddy's ACM 523) sometimes keeps extra copies of a duplicated hull vertex, and sometimes keeps a point that lies on a hull edge. `mclust/chull.py` does not reproduce this.

Facts from the battery in `proof/chull-r.R` (4003 cases, `docs/output/chull-battery-compare.txt`):

- The de-duplicated monotone chain matches R on 3974 cases.
- 14 cases differ by duplicates. R keeps 2 to 4 copies of one vertex. In `ELLIPSE1`, R keeps both copies of one axis vertex (indices 16 and 32) but only one copy of the other (48, not 0). Those copies are coincident, so the coordinates alone do not say which copy R keeps.
- 15 cases differ by a collinear point on an edge.
- R's R-level step sorts by angle about `colMeans(x[res, ])`, which counts duplicates. The port uses the centroid of unique vertices, so the order also changes once duplicates are kept.

Tried and not matching (Quickhull-style recursion, `probe` scripts not kept):

- Zero-distance points included in the side sets (non-strict side tests), with lexicographic extremes: at most 3849 of 4003, below the 3974 of the de-duplicated chain.
- Keeping only zero-distance copies of the chosen vertex: 2161 to 3713 of 4003, depending on the rule and tie order.

Index-level check (same battery, 4003 cases, R's 1-based output converted to 0-based): the de-duplicated chain with `first` copy gives 2514 exact index lists, with `last` copy 2162, keeping all copies 1692, and keeping all copies only at the min-x and max-x vertices 1738. Monotone chains with `<= 0` pops give 2072 to 2103 and with `< 0` pops give 746, because collinear points stay. No simple copy rule reproduces R's index lists, so the duplicate rule is a gap.

The C source is not on this machine (`/usr/lib/R` has only the compiled library). Reproducing the rule needs Eddy's array order, not a side test. Do not patch the ellipse vertices alone to get 61 for ELLIPSE1.

Copies kept by R's `chull` on the mclust filled-ellipse inputs (`mvn2plot` 64-point xy, 0-based indices; the pairs are the four duplicate pairs of each ellipse):

- ELLIPSE1 (61 vertices): 15/31 keeps 15; 16/32 keeps both; 0/48 keeps 48; 47/63 keeps 47.
- ELLIPSE2 (60): 15/31 keeps 31; 16/32 keeps 32; 0/48 keeps 48; 47/63 keeps 63.
- ELLIPSE3 (60): 15/31 keeps 31; 16/32 keeps 16; 0/48 keeps 0; 47/63 keeps 47.

Pairs 16/32 and 0/48 are exact copies, so their coordinates cannot say which copy R keeps. The same exact pair is kept twice on ELLIPSE1 and once on ELLIPSE2 and ELLIPSE3. The choice depends on the whole set and its order, not on the point. Checked on 1500 scratch random sets (grid, grid with copies, continuous with copies; R `chull` output): first-copy index sets match 271, last-copy 288, all-copies 105, and distinct-coordinate sets 1484. R keeps more than one copy in 121 sets. Duplicated hull points keep all copies in about 4 to 5 percent of cases. Adjacency of the copies in the input, index 0, and being an x-extreme do not predict it. Conclusion: no copy rule is found; keep the port as is.
