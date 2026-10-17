# R reference values and timings for the kernel batch: sfitted (through
# fitted.locfit), locfit.quasi, locfit.robust, locfit.censor, lscv.exact,
# and lscv (the density LSCV path).
#
# Run from the repository root:
#   Rscript packages/locfit/proof/kernel_r.R
#
# Every value comes from calling the real locfit 1.5-9.12 functions on the
# fixed inputs written by kernel_inputs_r.R. The explicit ev = dat() is used
# for the fits: R's default ev = rbox() needs kd-tree interpolation, which the
# Python side does not have. lscv is R's density LSCV (geth = 6) at the data. Timing: one untimed call, then the median over 20
# samples. Each sample is a loop of K calls; the reported time is divided by K.

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
library(locfit, lib.loc = lib)

out <- "packages/locfit/docs/output"
dir.create(out, recursive = TRUE, showWarnings = FALSE)

inp <- read.csv(file.path(out, "locfit_kernel_inputs.csv"))
x <- inp$x
y <- inp$y
cens <- inp$cens
w <- inp$w
dsamp <- read.csv(file.path(out, "locfit_kernel_dsamp.csv"))$dsamp

K <- 20L

calls <- list(
  sfitted = function() fitted(locfit.raw(x, y, ev = dat())),
  quasi = function() fitted(locfit.quasi(x, y, weights = w, ev = dat())),
  robust = function() fitted(locfit.robust(x, y, ev = dat())),
  censor = function() fitted(locfit.censor(x, y, cens, ev = dat())),
  lscv_exact_h05 = function() lscv.exact(dsamp, h = 0.5),
  lscv_exact_h03 = function() lscv.exact(dsamp, h = 0.3),
  lscv_dat_deg2 = function() lscv(dsamp, ev = dat()),
  lscv_dat_deg1 = function() lscv(dsamp, ev = dat(), deg = 1),
  lscv_dat_deg0 = function() lscv(dsamp, ev = dat(), deg = 0),
  lscv_dat_alpha05 = function() lscv(dsamp, ev = dat(), alpha = 0.5)
)

fmt <- function(v) paste(sprintf("%.17g", as.numeric(v)), collapse = ",")
values <- vapply(calls, function(f) fmt(f()), character(1))
writeLines(paste(names(values), values, sep = ","),
           file.path(out, "locfit_kernel_r_values.txt"))

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

timing <- vapply(calls, time_call, numeric(1))
writeLines(sprintf("%s,%.17g", names(timing), timing),
           file.path(out, "locfit_kernel_r_timing.txt"))

print(values)
print(timing)
