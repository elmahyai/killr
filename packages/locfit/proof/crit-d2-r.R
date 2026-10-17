# R reference values and timings for crit() at d = 2 (locfit 1.5-9.12).
#
# Run from the repository root:
#   Rscript packages/locfit/proof/crit-d2-r.R
#
# Values come from the real locfit crit(), which calls the C routine scritval.
# The fixed fit is locfit(y ~ x1 + x2) on a fixed 8 x 8 grid. A fit carries
# only its critical-value object (fit$critval), so the fit check reads that
# object; its const and d are printed so the Python proof can use the same
# inputs.
#
# Timing: one untimed call, then the median of 20 timed single calls.
# Sys.time() is the clock.

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
library(locfit, lib.loc = lib)

out <- "packages/locfit/docs/output"
dir.create(out, recursive = TRUE, showWarnings = FALSE)

g <- expand.grid(x1 = seq(0, 1, length.out = 8), x2 = seq(0, 1, length.out = 8))
g$y <- sin(2 * pi * g$x1) + cos(3 * g$x2) + 0.1 * g$x1 * g$x2
fit2 <- locfit(y ~ x1 + x2, data = g)

calls <- list(
  d2_c01_cov095 = function() crit(const = c(0, 1), d = 2, cov = 0.95)$crit.val,
  d2_c01_cov090 = function() crit(const = c(0, 1), d = 2, cov = 0.90)$crit.val,
  d2_c001_cov095 = function() crit(const = c(0, 0, 1), d = 2, cov = 0.95)$crit.val,
  d2_c021_cov095 = function() crit(const = c(0.2, 0.5, 1), d = 2, cov = 0.95)$crit.val
)

fmt <- function(v) sprintf("%.17g", as.numeric(v))
values <- vapply(calls, function(f) fmt(f()), character(1))
values <- c(values, fit2_critval = fmt(crit(fit2)$crit.val))
writeLines(paste(names(values), values, sep = ","),
           file.path(out, "crit-d2-r_values.txt"))

time_call <- function(f) {
  f()
  samples <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- Sys.time()
    f()
    samples[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
  }
  median(samples)
}

timing <- vapply(calls, time_call, numeric(1))
writeLines(sprintf("%s,%.17g", names(timing), timing),
           file.path(out, "crit-d2-r_timing.txt"))

cat("fit2 critval const:", fit2$critval$const, " d:", fit2$critval$d,
    " cov:", fit2$critval$cov, "\n")
print(values)
print(timing)
