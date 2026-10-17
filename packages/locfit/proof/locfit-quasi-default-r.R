# R reference for locfit.quasi() on R's default ev = rbox() (kd-tree), locfit 1.5-9.12.
# Run from the repository root:
#   Rscript --slave packages/locfit/proof/locfit-quasi-default-r.R
#
# Reads the fixed inputs written by locfit-default-r.R (docs/output/locfit_default_r).
# Writes packages/locfit/docs/output/locfit_quasi_default_r/:
#   <case>_fitted.csv   fitted(fit) at the data
#   <case>_eva.csv      fit$eva$coef without the trailing deg column
#   <case>_xev.csv      fit$eva$xev, the vertices (flat)
#   <case>_dp.csv       lk, df1, df2, rv, rsc
#   timing.csv          case,ms: median over 20 timed calls (one untimed call first)

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
suppressPackageStartupMessages(library(locfit, lib.loc = lib))
stopifnot(as.character(packageVersion("locfit")) == "1.5.9.12")

inref <- "packages/locfit/docs/output/locfit_default_r"
outdir <- "packages/locfit/docs/output/locfit_quasi_default_r"
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

rd <- function(name) as.matrix(read.csv(file.path(inref, paste0(name, ".csv")), header = FALSE))
x1 <- as.vector(rd("in_x1"))
y1 <- as.vector(rd("in_y1"))
x2 <- rd("in_x2")
y2 <- as.vector(rd("in_y2"))

wr_vec <- function(name, v)
  writeLines(sprintf("%.17g", as.numeric(v)), file.path(outdir, paste0(name, ".csv")))
wr_mat <- function(name, m) {
  m <- as.matrix(m)
  storage.mode(m) <- "double"
  writeLines(apply(m, 1, function(r) paste(sprintf("%.17g", r), collapse = ",")),
             file.path(outdir, paste0(name, ".csv")))
}

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
  quasi_d1 = function() locfit.quasi(x1, y1),
  quasi_d2 = function() locfit.quasi(x2, y2)
)

timing <- character(0)
for (nm in names(cases)) {
  fit <- cases[[nm]]()
  wr_vec(paste0(nm, "_fitted"), fitted(fit))
  ev <- fit$eva$coef
  wr_mat(paste0(nm, "_eva"), ev[, -ncol(ev), drop = FALSE])
  wr_vec(paste0(nm, "_xev"), fit$eva$xev)
  wr_vec(paste0(nm, "_dp"), fit$dp[c("lk", "df1", "df2", "rv", "rsc")])
  timing <- c(timing, sprintf("%s,%.17g", nm, time_ms(cases[[nm]])))
  cat(nm, "vertices:", nrow(ev), "\n")
}
writeLines(timing, file.path(outdir, "timing.csv"))
print(timing)
