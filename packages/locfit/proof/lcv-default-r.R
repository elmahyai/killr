# R reference for lcv() on R's default ev = rbox() (kd-tree), locfit 1.5-9.12.
# Run from the repository root, after locfit-default-r.R has written the inputs:
#   Rscript --slave packages/locfit/proof/lcv-default-r.R
#
# Reads docs/output/locfit_default_r/in_*.csv (written by locfit-default-r.R).
# Writes packages/locfit/docs/output/lcv_default_r/:
#   <case>.csv        lik, infl, vari, cv (one value per line, R's lcv order)
#   timing.csv        case,ms: median over 20 timed calls (one untimed call first)

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
suppressPackageStartupMessages(library(locfit, lib.loc = lib))
stopifnot(as.character(packageVersion("locfit")) == "1.5.9.12")

inref <- "packages/locfit/docs/output/locfit_default_r"
stopifnot(file.exists(file.path(inref, "in_y1.csv")))
outdir <- "packages/locfit/docs/output/lcv_default_r"
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
  lcv_d1 = list(f = function() lcv(x1, y1)),
  lcv_d2 = list(f = function() lcv(x2, y2))
)

timing <- character(0)
for (nm in names(cases)) {
  cs <- cases[[nm]]
  v <- cs$f()
  stopifnot(identical(names(v), c("lik", "infl", "vari", "cv")))
  writeLines(sprintf("%.17g", as.numeric(v)), file.path(outdir, paste0(nm, ".csv")))
  timing <- c(timing, sprintf("%s,%.17g", nm, time_ms(cs$f)))
  cat(nm, ":", as.numeric(v), "\n")
}
writeLines(timing, file.path(outdir, "timing.csv"))
print(timing)
