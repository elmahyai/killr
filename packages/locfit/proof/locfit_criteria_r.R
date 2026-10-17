# R reference values and timings for the seven locfit helpers:
# aic, ang, cp, crit, dat, expit, gcv.
#
# Run from the repository root:
#   Rscript packages/locfit/proof/locfit_criteria_r.R
#
# Every value comes from calling the real locfit 1.5-9.12 functions. The
# criteria are called as aic(x, y, ev = dat()) so that R fits directly at the
# data, the same direct fit the Python side makes through crates/locfit.
# Timing: one untimed call, then the median over 20 samples. Each sample is a
# loop of K calls, and the reported time is the sample time divided by K.

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
library(locfit, lib.loc = lib)

out <- "packages/locfit/docs/output"
dir.create(out, recursive = TRUE, showWarnings = FALSE)

K <- 100L
x <- seq(0, 1, length.out = 12)
y <- sin(2 * pi * x) + 0.1 * cos(7 * x)

calls <- list(
  aic = function() unname(aic(x, y, ev = dat())),
  cp = function() unname(cp(x, y, ev = dat(), sig2 = 1)),
  gcv = function() unname(gcv(x, y, ev = dat())),
  crit = function() crit(const = c(0, 1), d = 1, cov = 0.95)$crit.val,
  crit_cov090 = function() crit(const = c(0, 1), d = 1, cov = 0.9)$crit.val,
  crit_d2 = function() crit(const = c(0, 1), d = 2, cov = 0.95)$crit.val,
  dat = function() {
    z <- dat()
    c(as.numeric(z$type == "crossval"), z$xev, z$mg, z$cut, z$ll, z$ur)
  },
  dat_cv = function() {
    z <- dat(TRUE)
    c(as.numeric(z$type == "crossval"), z$xev, z$mg, z$cut, z$ll, z$ur)
  },
  expit = function() expit(c(-3, 0, 2)),
  ang = function() as.numeric(ang(c(-1, 0, 1)))
)

values <- vapply(calls, function(f) paste(sprintf("%.17g", as.numeric(f())),
                                          collapse = ","), character(1))
writeLines(paste(names(values), values, sep = ","),
           file.path(out, "locfit_criteria_r_values.txt"))

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

timing <- vapply(calls[c("aic", "cp", "gcv", "crit", "dat", "expit", "ang")],
                 time_call, numeric(1))
writeLines(sprintf("%s,%.17g", names(timing), timing),
           file.path(out, "locfit_criteria_r_timing.txt"))

print(values)
print(timing)
