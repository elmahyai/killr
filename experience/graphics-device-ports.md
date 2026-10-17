# Graphics device ports

When an R routine only draws on the current graphics device and returns
`NULL`, a Matplotlib port should create equivalent figures and return `None`.
Proofs compare that no-return contract and save both rendered outputs.

A lattice plot returns a trellis object, so the R proof can read what was plotted without tracing:
`p$panel.args[[1]]` holds the plotted `x`, `y`, and `subscripts`, and `environment(p$panel)` holds the
plot function's locals (for example `abl`, `id`, `idLabels`). `trace()` on lattice functions did not
record calls, because the nlme namespace imports them.
