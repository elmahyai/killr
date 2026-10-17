# R reference values and timings for crit() at d = 3 (locfit 1.5-9.12).
#
# Run from the repository root:
#   Rscript packages/locfit/proof/crit-d3-r.R
#
# Values come from the real locfit crit(), which calls the C routine scritval.
# The fixed fit is locfit(y ~ x1 + x2 + x3) on a fixed 4 x 4 x 4 grid. A fit carries
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

g <- expand.grid(x1 = seq(0, 1, length.out = 4), x2 = seq(0, 1, length.out = 4),
                 x3 = seq(0, 1, length.out = 4))
g$y <- sin(2 * pi * g$x1) + cos(3 * g$x2) + g$x3^2 + 0.1 * g$x1 * g$x2
fit3 <- locfit(y ~ x1 + x2 + x3, data = g)

calls <- list(
  d3_c01_cov095 = function() crit(const = c(0, 1), d = 3, cov = 0.95)$crit.val,
  d3_c01_cov090 = function() crit(const = c(0, 1), d = 3, cov = 0.90)$crit.val,
  d3_c0001_cov095 = function() crit(const = c(0, 0, 0, 1), d = 3, cov = 0.95)$crit.val,
  d3_c0215_cov095 = function() crit(const = c(0.2, 0.5, 1, 0.7), d = 3, cov = 0.95)$crit.val
)

fmt <- function(v) sprintf("%.17g", as.numeric(v))
values <- vapply(calls, function(f) fmt(f()), character(1))
values <- c(values, fit3_critval = fmt(crit(fit3)$crit.val))
writeLines(paste(names(values), values, sep = ","),
           file.path(out, "crit-d3-r_values.txt"))

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
           file.path(out, "crit-d3-r_timing.txt"))

cat("fit3 critval const:", fit3$critval$const, " d:", fit3$critval$d,
    " cov:", fit3$critval$cov, "\n")
print(values)
print(timing)
