# R reference for hatmatrix(), locfit 1.5-9.12. Run from the repository root:
#   Rscript --slave packages/locfit/proof/hatmatrix-r.R
#
# 1. R's hatmatrix() on the default ev = rbox() path: the error is recorded.
#    R errors for every n tried, so there is no default-path reference value.
# 2. The data-path reference used by the Python probe, t(locfit.raw(geth = 1,
#    ev = dat())) on the first 40 rows of the fixed d = 1 input. It is NOT the
#    default path and is only a check of the probe.
# Writes packages/locfit/docs/output/hatmatrix_r/: default_error.txt,
#   dat_hat.csv (40 x 40), timing.csv (median of 20 timed calls, one untimed first).

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
suppressPackageStartupMessages(library(locfit, lib.loc = lib))
stopifnot(as.character(packageVersion("locfit")) == "1.5.9.12")

inref <- "packages/locfit/docs/output/locfit_default_r"
outdir <- "packages/locfit/docs/output/hatmatrix_r"
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)
x1 <- as.matrix(read.csv(file.path(inref, "in_x1.csv"), header = FALSE))[1:40, , drop = FALSE]
y1 <- as.vector(as.matrix(read.csv(file.path(inref, "in_y1.csv"), header = FALSE)))[1:40]

err <- try(hatmatrix(y1 ~ x1[, 1]), silent = TRUE)
msg <- if (inherits(err, "try-error")) conditionMessage(attr(err, "condition")) else "no error"
writeLines(c("hatmatrix(y ~ x) default ev = rbox(), n = 40:", msg), file.path(outdir, "default_error.txt"))
cat("default:", msg, "\n")

H <- t(locfit.raw(x1, y1, geth = 1, ev = dat()))
write.table(H, file.path(outdir, "dat_hat.csv"), sep = ",", row.names = FALSE, col.names = FALSE)

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
f <- function() locfit.raw(x1, y1, geth = 1, ev = dat())
writeLines(sprintf("dat_path,%.17g", time_ms(f)), file.path(outdir, "timing.csv"))
