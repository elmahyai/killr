# R reference values and timings for gam.lf var (locfit 1.5-9.12).
#
# Run from the repository root:
#   Rscript packages/locfit/proof/gam-lf-var-r.R
#
# var is the third element of gam.lf(x, y, w): locfit.raw(geth = 4) returns
# z$wdes[n * (p + 2) + p * p + (1:n)], a slice of the design work array. The
# values compared are var for the three default kd-tree cases.
#
# Timing: one untimed call, then the median of 20 samples. Each sample is a
# loop of K calls timed with Sys.time(); the reported time is the sample time
# divided by K. Timings are for the first case (g1_default).

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
library(locfit, lib.loc = lib)

out <- "packages/locfit/docs/output"
dir.create(out, recursive = TRUE, showWarnings = FALSE)

K <- 100L
g1 <- list(x = seq(0, 1, length.out = 12),
           y = sin(2 * pi * seq(0, 1, length.out = 12)) +
             0.1 * cos(7 * seq(0, 1, length.out = 12)),
           w = seq(0.5, 2, length.out = 12))
p40 <- qnorm(ppoints(40))
g2 <- list(x = p40, y = sin(p40) + 0.3 * cos(3 * p40), w = rep(1, 40))
x1 <- seq(0, 1, length.out = 30)
x2 <- (sin(1:30) + 1) / 2
g3 <- list(x = cbind(x1, x2), y = x1 + sin(4 * x2), w = 1 + x1)

cases <- list(
  g1_default = function() gam.lf(g1$x, g1$y, g1$w)$var,
  g2_default = function() gam.lf(g2$x, g2$y, g2$w)$var,
  g3_default = function() gam.lf(g3$x, g3$y, g3$w)$var
)

fmt <- function(v) paste(sprintf("%.17g", as.numeric(v)), collapse = ",")

values <- character(0)
for (nm in names(cases)) {
  v <- cases[[nm]]()
  values <- c(values, paste(nm, "var", fmt(v), sep = ","))
}
writeLines(values, file.path(out, "gam_lf_var_r_values.txt"))

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

timing <- time_call(function() gam.lf(g1$x, g1$y, g1$w))
writeLines(sprintf("gam.lf var,%.17g", timing), file.path(out, "gam_lf_var_r_timing.txt"))

print(values)
print(timing)
