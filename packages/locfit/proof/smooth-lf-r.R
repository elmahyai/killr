# R reference for smooth.lf() on R's default path (direct = FALSE, ev = rbox()),
# locfit 1.5-9.12. Run from the repository root:
#   Rscript --slave packages/locfit/proof/smooth-lf-r.R
#
# Reads the fixed inputs written by locfit-default-r.R (docs/output/locfit_default_r).
# Writes packages/locfit/docs/output/smooth_lf_r/:
#   <case>.csv   the smoothed y (one value per line)
#   timing.csv   case,ms: median over 20 timed calls (one untimed call first)

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
suppressPackageStartupMessages(library(locfit, lib.loc = lib))
stopifnot(as.character(packageVersion("locfit")) == "1.5.9.12")

inref <- "packages/locfit/docs/output/locfit_default_r"
stopifnot(file.exists(file.path(inref, "in_x1.csv")))
outdir <- "packages/locfit/docs/output/smooth_lf_r"
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

rd <- function(name) as.matrix(read.csv(file.path(inref, paste0(name, ".csv")), header = FALSE))
x1 <- rd("in_x1")
y1 <- as.vector(rd("in_y1"))
x2 <- rd("in_x2")
y2 <- as.vector(rd("in_y2"))

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
  smooth_lf_d1 = list(f = function() smooth.lf(x1, y1)),
  smooth_lf_d2 = list(f = function() smooth.lf(x2, y2)),
  smooth_lf_d1_alpha = list(f = function() smooth.lf(x1, y1, alpha = 0.5, deg = 1))
)

timing <- character(0)
for (nm in names(cases)) {
  cs <- cases[[nm]]
  v <- cs$f()
  stopifnot(identical(names(v)[1:2], c("x", "y")))
  writeLines(sprintf("%.17g", as.numeric(v$y)), file.path(outdir, paste0(nm, ".csv")))
  timing <- c(timing, sprintf("%s,%.17g", nm, time_ms(cs$f)))
  cat(nm, ": first y =", head(as.numeric(v$y), 3), "\n")
}
writeLines(timing, file.path(outdir, "timing.csv"))
print(timing)
