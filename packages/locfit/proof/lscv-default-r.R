# R reference for lscv() on R's default ev = rbox() (kd-tree), locfit 1.5-9.12.
# Run from the repository root:
#   Rscript --slave packages/locfit/proof/lscv-default-r.R
#
# Reads the fixed inputs written by locfit-default-r.R (docs/output/locfit_default_r).
# Writes packages/locfit/docs/output/lscv_default_r/:
#   <case>.csv     R's two values of lscv(): criterion and degrees of freedom
#   timing.csv     case,ms: median over 20 timed calls (one untimed call first)
# The d = 2 case is R's density path with the two-dimensional integral (not
# available in R's own dens_integrate, which warns and returns 0); it is recorded
# here as the reference value, and the Python side reports it as not translated.

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
suppressPackageStartupMessages(library(locfit, lib.loc = lib))
stopifnot(as.character(packageVersion("locfit")) == "1.5.9.12")

inref <- "packages/locfit/docs/output/locfit_default_r"
outdir <- "packages/locfit/docs/output/lscv_default_r"
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

rd <- function(name) as.matrix(read.csv(file.path(inref, paste0(name, ".csv")), header = FALSE))
x1 <- as.vector(rd("in_x1"))
x2 <- rd("in_x2")

# One untimed call, then the median of 20 timed calls (Sys.time).
time_ms <- function(f) {
  f()
  s <- numeric(20)
  for (k in 1:20) {
    t0 <- Sys.time()
    f()
    s[k] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
  }
  median(s)
}

cases <- list(
  lscv_d1 = function() suppressWarnings(lscv(x1)),
  lscv_d2 = function() suppressWarnings(lscv(x2))
)

timing <- character(0)
for (nm in names(cases)) {
  v <- cases[[nm]]()
  stopifnot(length(v) == 2)
  writeLines(sprintf("%.17g", as.numeric(v)), file.path(outdir, paste0(nm, ".csv")))
  timing <- c(timing, sprintf("%s,%.17g", nm, time_ms(cases[[nm]])))
  cat(nm, ":", as.numeric(v), "\n")
}
writeLines(timing, file.path(outdir, "timing.csv"))
print(timing)
