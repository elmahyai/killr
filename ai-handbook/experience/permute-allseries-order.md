# permute allSeries row order

- R's `allSeries(n, nperms, mirror)` fills row `i` (1-based) with `seq(i, length = n) %% n + 1`. So the rows begin 2, 3, ..., n, 1, and row `n` is the identity. A Python version that starts at row 1 with the identity gives the same rows in a different order.
- The order matters when `shuffleSet(..., check = TRUE)` takes the complete path. It samples rows from `allPerms`, so a series design returns a different row for the same seed.
- With `mirror = TRUE`, rows `n+1` to `2n` are rows `1` to `n` with the columns reversed.
- Checked by `packages/permute/proof/allSeries-order-r.R` and `allSeries-order-py.py`.
