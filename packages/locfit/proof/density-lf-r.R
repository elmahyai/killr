# R reference values and timings for density.lf (locfit 1.5-9.12).
#
# Run from the repository root:
#   Rscript packages/locfit/proof/density-lf-r.R
#
# Cases are the fixed samples below, with density.lf's defaults (window
# "gaussian", deg 0, link "ident", family "density", ev = lfgrid(n, from, to)).
# The R side calls the real locfit function; nothing here reimplements it.
#
# Timing: one untimed call, then the median of 20 samples. Each sample is a loop
# of K calls timed with Sys.time(); the reported time is the sample time
# divided by K. Timings are for the default case (xd_default).

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
library(locfit, lib.loc = lib)

out <- "packages/locfit/docs/output"
dir.create(out, recursive = TRUE, showWarnings = FALSE)

K <- 100L
xd <- qnorm(seq(0.05, 0.95, length.out = 20))
x2 <- qnorm(ppoints(60)) * 1.3 + 0.2

cases <- list(
  xd_default = function() density.lf(xd, n = 50),
  xd_rect = function() density.lf(xd, n = 50, window = "rectangular"),
  xd_tria = function() density.lf(xd, n = 50, window = "triangular"),
  xd_tcub = function() density.lf(xd, n = 50, window = "tcub"),
  x2_default = function() density.lf(x2, n = 50),
  x2_width = function() density.lf(x2, n = 80, width = 0.8)
)

fmt <- function(v) paste(sprintf("%.17g", as.numeric(v)), collapse = ",")

values <- character(0)
for (nm in names(cases)) {
  d <- cases[[nm]]()
  values <- c(values,
              paste(nm, "x", fmt(d$x), sep = ","),
              paste(nm, "y", fmt(d$y), sep = ","))
}
writeLines(values, file.path(out, "density_lf_r_values.txt"))

time_call <- function(f) {
  f()
  samples <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- Sys.time()
    for (j in seq_len(K)) f()
    samples[i] <- as.numeric(Sys.time() - t0) * 1000
  }
  median(samples) / K
}

timing <- time_call(cases$xd_default)
writeLines(sprintf("density.lf,%.17g", timing),
           file.path(out, "density_lf_r_timing.txt"))

print(values)
print(timing)
