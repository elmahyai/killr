# R reference values and timings for kappa0() at d = 2 (locfit 1.5-9.12).
#
# Run from the repository root:
#   Rscript packages/locfit/proof/kappa0-d2-r.R
#
# kappa0(formula, cov, ev = lfgrid(20)) fits with geth = 2 on the grid and
# returns crit(const = z$const, d = z$d, cov = cov). The values are the real
# kappa0() of locfit 1.5-9.12, so R computes the tube constants itself.
#
# Data: n = 100 points in [0, 1]^2 from a fixed permutation:
#   x1 = (i + 0.5) / 100,  x2 = ((37 i) mod 100 + 0.5) / 100,  i = 0..99
#   y = sin(2 pi x1) + cos(3 x2) + 0.1 x1 x2.
#
# Timing: one untimed call, then the median of 20 timed single calls.
# Sys.time() is the clock.

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
library(locfit, lib.loc = lib)

out <- "packages/locfit/docs/output"
dir.create(out, recursive = TRUE, showWarnings = FALSE)

i <- 0:99
x1 <- (i + 0.5) / 100
x2 <- ((37 * i) %% 100 + 0.5) / 100
y <- sin(2 * pi * x1) + cos(3 * x2) + 0.1 * x1 * x2
X <- cbind(x1, x2)

fmt <- function(v) paste(sprintf("%.17g", as.numeric(v)), collapse = ",")

k95 <- kappa0(y ~ X, cov = 0.95)
k90 <- kappa0(y ~ X, cov = 0.90)
values <- c(
  d2_const = fmt(k95$const),
  d2_d = fmt(k95$d),
  d2_cov095_crit = fmt(k95$crit.val),
  d2_cov090_crit = fmt(k90$crit.val)
)
writeLines(paste(names(values), values, sep = ","),
           file.path(out, "kappa0-d2-r_values.txt"))

time_call <- function(f) {
  f()
  samples <- numeric(20)
  for (j in seq_len(20)) {
    t0 <- Sys.time()
    f()
    samples[j] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
  }
  median(samples)
}

timing <- c(d2_kappa0 = time_call(function() kappa0(y ~ X, cov = 0.95)))
writeLines(sprintf("%s,%.17g", names(timing), timing),
           file.path(out, "kappa0-d2-r_timing.txt"))

print(values)
print(timing)
