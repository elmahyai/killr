# R reference values for scb() (default ev = lfgrid(20), simul = TRUE, type = 1),
# locfit 1.5-9.12. Run from the repository root:
#   Rscript --slave packages/locfit/proof/scb-r.R
# scb is not translated: the default call runs locfit's C band path (geth = 81:
# scb.c, scb_crit.c, simul.c), which crates/locfit does not have. These are the
# reference values for a future kernel port.
# Writes docs/output/scb_r/<case>_<field>.csv and timing.csv (median of 20 timed
# calls, one untimed call first).
lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
suppressPackageStartupMessages(library(locfit, lib.loc = lib))
inref <- "packages/locfit/docs/output/locfit_default_r"
outdir <- "packages/locfit/docs/output/scb_r"
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)
rd <- function(name) as.matrix(read.csv(file.path(inref, paste0(name, ".csv")), header = FALSE))
x1 <- rd("in_x1"); y1 <- as.vector(rd("in_y1"))
x2 <- rd("in_x2"); y2 <- as.vector(rd("in_y2"))
time_ms <- function(f) {
  f()
  s <- numeric(20)
  for (k in 1:20) {
    t0 <- Sys.time(); f()
    s[k] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
  }
  median(s)
}
cases <- list(scb_d1 = function() scb(x1, y1), scb_d2 = function() scb(x2, y2))
timing <- character(0)
for (nm in names(cases)) {
  z <- suppressWarnings(cases[[nm]]())
  for (f in c("coef", "sd", "lower", "upper")) {
    v <- z[[f]]
    if (is.null(v)) next
    writeLines(sprintf("%.17g", as.numeric(v)), file.path(outdir, paste0(nm, "_", f, ".csv")))
  }
  timing <- c(timing, sprintf("%s,%.17g", nm, time_ms(function() suppressWarnings(cases[[nm]]()))))
}
writeLines(timing, file.path(outdir, "timing.csv"))
print(timing)
print(names(z))
