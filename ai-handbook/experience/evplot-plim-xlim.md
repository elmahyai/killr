# evplot plim always fails in R

`evplot.default` sets `xlim <- c(-log(-log(plim)))` when `plim` is given. That makes
`xlim` one number, not two. R then fails in `plot.window` with
`invalid 'xlim' value`, so `evplot(y, plim = p)` errors for every `p`, with or
without data or `qfunc`.

The Python translation raises the same `ValueError("invalid 'xlim' value")` at the
same step, after the plotting positions and the `ylim` widening are computed, and
before anything is drawn. Do not make `plim` work. The proof checks this error
message exactly.
