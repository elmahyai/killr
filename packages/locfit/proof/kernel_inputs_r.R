# Fixed inputs for the kernel batch: sfitted, locfit.quasi, locfit.robust,
# locfit.censor, lscv.exact, and the density LSCV (lscv) when it is ported.
#
# Run from the repository root:
#   Rscript packages/locfit/proof/kernel_inputs_r.R
#
# Writes packages/locfit/docs/output/locfit_kernel_inputs.csv (x, y, cens, w),
# which the R and Python proofs both read. The sample is fixed by set.seed.

out <- "packages/locfit/docs/output"
dir.create(out, recursive = TRUE, showWarnings = FALSE)

set.seed(20261017)
n <- 40
x <- sort(runif(n))
y <- sin(2 * pi * x) + 0.25 * rnorm(n)
cens <- as.numeric(y > quantile(y, 0.85))
w <- seq(0.5, 2, length.out = n)

inp <- data.frame(x = x, y = y, cens = cens, w = w)
write.csv(inp, file.path(out, "locfit_kernel_inputs.csv"), row.names = FALSE)

# A density sample for lscv and lscv.exact, fixed the same way.
set.seed(20261018)
dsamp <- qnorm(sort(runif(30, 0.02, 0.98)))
write.csv(data.frame(dsamp = dsamp), file.path(out, "locfit_kernel_dsamp.csv"),
          row.names = FALSE)
cat("inputs written\n")
