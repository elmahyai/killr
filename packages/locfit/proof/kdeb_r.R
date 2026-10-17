# R reference values and timings for kdeb (locfit 1.5-9.12), the bandwidth
# selector that R runs in C through .C("kdeb").
#
# Run from the repository root:
#   Rscript packages/locfit/proof/kdeb_r.R
#
# Inputs are the fixed samples written by kernel_inputs_r.R
# (locfit_kernel_dsamp.csv and locfit_kernel_inputs.csv).
#
# Timing: one untimed call, then the median of 20 timed calls, each timed with
# Sys.time(). The reported time is in milliseconds.

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
library(locfit, lib.loc = lib)

out <- "packages/locfit/docs/output"
dir.create(out, recursive = TRUE, showWarnings = FALSE)

dsamp <- read.csv(file.path(out, "locfit_kernel_dsamp.csv"))$dsamp
xin <- read.csv(file.path(out, "locfit_kernel_inputs.csv"))$x

cases <- list(
  dsamp_default = function() kdeb(dsamp),
  inputs_x_default = function() kdeb(xin),
  dsamp_h0h1 = function() kdeb(dsamp, h0 = 0.05, h1 = 0.8,
                                meth = c("SJPI", "AIC", "GKK")),
  dsamp_meth_subset = function() kdeb(dsamp, meth = c("LSCV", "BCV"))
)

fmt <- function(v) paste(sprintf("%.17g", as.numeric(v)), collapse = ",")

# One line per case: case, method names (joined by |), values (comma-separated).
values <- character(0)
for (nm in names(cases)) {
  v <- cases[[nm]]()
  values <- c(values, paste(nm, paste(names(v), collapse = "|"), fmt(v), sep = ","))
}
writeLines(values, file.path(out, "locfit_kdeb_r_values.txt"))

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

timing <- vapply(cases, time_call, numeric(1))
writeLines(sprintf("%s,%.17g", names(timing), timing),
           file.path(out, "locfit_kdeb_r_timing.txt"))

print(values)
print(timing)
