# R reference values and timings for gam.lf with non-default arguments
# (locfit 1.5-9.12): one case, alpha = 0.5, deg = 1, kern = "rect" on g1.
#
# Run from the repository root:
#   Rscript packages/locfit/proof/gam-lf-nondefault-r.R
#
# The values compared are residuals, var, and nl.df. ev stays the default
# rbox() (the kd-tree).
#
# Timing: one untimed call, then the median of 20 samples. Each sample is a
# loop of K calls timed with Sys.time(); the reported time is the sample time
# divided by K.

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
library(locfit, lib.loc = lib)

out <- "packages/locfit/docs/output"
dir.create(out, recursive = TRUE, showWarnings = FALSE)

K <- 100L
g1 <- list(x = seq(0, 1, length.out = 12),
           y = sin(2 * pi * seq(0, 1, length.out = 12)) +
             0.1 * cos(7 * seq(0, 1, length.out = 12)),
           w = seq(0.5, 2, length.out = 12))

call_nd <- function() gam.lf(g1$x, g1$y, g1$w, alpha = 0.5, deg = 1, kern = "rect")

fmt <- function(v) paste(sprintf("%.17g", as.numeric(v)), collapse = ",")

nd <- call_nd()
values <- c(paste("g1_nondefault", "residuals", fmt(nd$residuals), sep = ","),
            paste("g1_nondefault", "nl.df", fmt(nd$nl.df), sep = ","),
            paste("g1_nondefault", "var", fmt(nd$var), sep = ","))
writeLines(values, file.path(out, "gam_lf_nondefault_r_values.txt"))

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

timing <- time_call(call_nd)
writeLines(sprintf("gam.lf nondefault,%.17g", timing), file.path(out, "gam_lf_nondefault_r_timing.txt"))

print(values)
print(timing)
