# R reference values and timings for the four functions still open in locfit:
# crit, hatmatrix, kappa0, lcv.
#
# Run from the repository root:
#   Rscript packages/locfit/proof/locfit_four_r.R
#
# Inputs are the fixed (x, y) written by kernel_inputs_r.R. Values come from the
# real locfit 1.5-9.12 functions. hatmatrix is the locfit.raw(geth = 1) operator
# with ev = dat(), transposed; R's hatmatrix() itself stops on this data ("data
# is too long"), so that is recorded as a string, not compared.
#
# Timing: one untimed call, then the median of 20 timed calls. Sys.time().

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
library(locfit, lib.loc = lib)

out <- "packages/locfit/docs/output"
dir.create(out, recursive = TRUE, showWarnings = FALSE)

inp <- read.csv(file.path(out, "locfit_kernel_inputs.csv"))
x <- inp$x
y <- inp$y
xm <- matrix(x, ncol = 1)
n <- length(y)

fmt <- function(v) paste(sprintf("%.17g", as.numeric(v)), collapse = ",")

hatmatrix_ref <- function() t(locfit.raw(xm, y, ev = dat(), geth = 1))

kappa0_default <- function() {
  v <- NULL
  capture.output(v <- suppressWarnings(kappa0(y ~ x, cov = 0.95)$crit.val))
  v
}

lcv_dat <- function() lcv(x, y, ev = dat())
lcv_default <- function() {
  v <- NULL
  capture.output(v <- suppressWarnings(lcv(x, y)))
  v
}

calls <- list(
  crit_d1 = function() crit(const = c(0, 1), d = 1, cov = 0.95)$crit.val,
  crit_d1_cov090 = function() crit(const = c(0, 1), d = 1, cov = 0.9)$crit.val,
  crit_d2 = function() crit(const = c(0, 1), d = 2, cov = 0.95)$crit.val,
  hatmatrix = function() as.vector(t(hatmatrix_ref())),
  kappa0_default = kappa0_default,
  lcv_dat = lcv_dat,
  lcv_default = lcv_default
)

values <- vapply(calls, function(f) fmt(f()), character(1))
writeLines(paste(names(values), values, sep = ","),
           file.path(out, "locfit_four_r_values.txt"))

time_call <- function(f) {
  f()
  samples <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- Sys.time()
    f()
    samples[i] <- as.numeric(Sys.time() - t0) * 1000
  }
  median(samples)
}

timing <- vapply(calls[c("crit_d1", "crit_d1_cov090", "crit_d2", "hatmatrix",
                         "kappa0_default", "lcv_dat")],
                 time_call, numeric(1))
writeLines(sprintf("%s,%.17g", names(timing), timing),
           file.path(out, "locfit_four_r_timing.txt"))

print(values)
print(timing)
