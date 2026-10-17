# R reference values and timings for gam.lf and density.lf.
#
# Run from the repository root:
#   Rscript packages/locfit/proof/locfit_smoothers_r.R
#
# gam.lf is shown twice: with the R default (ev = rbox(), the kd-tree vertex
# interpolation) and with ev = dat() (a direct fit at the data). The Python
# side can only reach the direct fit through crates/locfit, so the ev = dat()
# values are the comparison target. density.lf uses its R default.

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
library(locfit, lib.loc = lib)

out <- "packages/locfit/docs/output"
dir.create(out, recursive = TRUE, showWarnings = FALSE)

K <- 100L
x <- seq(0, 1, length.out = 12)
y <- sin(2 * pi * x) + 0.1 * cos(7 * x)
w <- seq(0.5, 2, length.out = 12)

xd <- qnorm(seq(0.05, 0.95, length.out = 20))

gam_ev <- function() gam.lf(x, y, w, ev = dat())
gam_default <- function() gam.lf(x, y, w)
density_default <- function() density.lf(xd, n = 50)

fmt <- function(v) paste(sprintf("%.17g", as.numeric(v)), collapse = ",")

g <- gam_ev()
d <- density_default()
gd <- gam_default()
values <- c(
  gam.lf_ev_residuals = fmt(g$residuals),
  gam.lf_ev_nl.df = fmt(g$nl.df),
  gam.lf_default_residuals = fmt(gd$residuals),
  gam.lf_default_nl.df = fmt(gd$nl.df),
  density.lf_x = fmt(d$x),
  density.lf_y = fmt(d$y)
)
writeLines(paste(names(values), values, sep = ","),
           file.path(out, "locfit_smoothers_r_values.txt"))

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

timing <- c(
  gam.lf_ev = time_call(gam_ev),
  gam.lf_default = time_call(gam_default),
  density.lf = time_call(density_default)
)
writeLines(sprintf("%s,%.17g", names(timing), timing),
           file.path(out, "locfit_smoothers_r_timing.txt"))

print(values)
print(timing)
