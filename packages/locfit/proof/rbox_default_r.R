# Proof (R side) for the default ev = rbox() path of locfit.censor, locfit.quasi,
# locfit.robust and lscv, against R locfit 1.5-9.12.
#
# Reads the fixed inputs written by locfit10_r.R (docs/output/locfit_ref/in_*.csv),
# so the R and Python proofs see the same numbers. Run from the repository root:
#   Rscript packages/locfit/proof/rbox_default_r.R
#
# Writes packages/locfit/docs/output/locfit_default_ref/:
#   <case>_fitted.csv     fitted(fit) at the data
#   <case>_se.csv         predict(fit, newdata = x, se.fit = TRUE)$se.fit at the data
#   <case>_eva.csv        fit$eva$coef: coef | nlx | t0 | lik | h | deg, one row per vertex
#   <case>_xev.csv        fit$eva$xev, the vertices (flat, row-major)
#   <case>_dp.csv         lk, df1, df2, rv, rsc
#   lscv_default.csv      lscv(dsamp): criterion, degrees of freedom
#   r_timing_default.csv  case,ms: median ms per call; one untimed call, then 20 timed calls
#                         (each timed with Sys.time())

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
suppressPackageStartupMessages(library(locfit, lib.loc = lib))
stopifnot(as.character(packageVersion("locfit")) == "1.5.9.12")

inref <- "packages/locfit/docs/output/locfit_ref"
outdir <- "packages/locfit/docs/output/locfit_default_ref"
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

rd <- function(name) as.matrix(read.csv(file.path(inref, paste0(name, ".csv")), header = FALSE))
x1 <- rd("in_x1")
y1 <- as.vector(rd("in_y1"))
cens1 <- as.vector(rd("in_cens1"))
x2 <- rd("in_x2")
y2 <- as.vector(rd("in_y2"))
dsamp <- as.vector(rd("in_dsamp"))
# Censoring for the two-dimensional check: the top of the first covariate.
cens2 <- as.numeric(x2[, 1] > 0.85)

wr_vec <- function(name, v)
  writeLines(sprintf("%.17g", as.numeric(v)), file.path(outdir, paste0(name, ".csv")))
wr_mat <- function(name, m) {
  m <- as.matrix(m)
  storage.mode(m) <- "double"
  lines <- apply(m, 1, function(r) paste(sprintf("%.17g", r), collapse = ","))
  writeLines(lines, file.path(outdir, paste0(name, ".csv")))
}

timed_ms <- function(f) {
  f()  # one untimed call
  s <- numeric(20)
  for (k in 1:20) {
    t0 <- Sys.time()
    f()
    s[k] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
  }
  median(s)
}

# Each case: the fit function, and the points at which se.fit is taken.
cases <- list(
  censor_d1 = list(f = function() locfit.censor(x1, y1, cens = cens1, alpha = 0.7, deg = 2,
                                                 kern = "tricube", kt = "sph"),
                   X = x1),
  quasi_d1 = list(f = function() locfit.quasi(x1, y1, alpha = 0.7, deg = 2,
                                               kern = "tricube", kt = "sph"),
                  X = x1),
  robust_d1 = list(f = function() locfit.robust(x1, y1, alpha = 0.7, deg = 2,
                                                 kern = "tricube", kt = "sph"),
                   X = x1),
  censor_d2 = list(f = function() locfit.censor(x2, y2, cens = cens2, alpha = 0.7, deg = 2,
                                                 kern = "tricube", kt = "sph"),
                   X = x2),
  quasi_d2 = list(f = function() locfit.quasi(x2, y2, alpha = 0.7, deg = 2,
                                               kern = "tricube", kt = "sph"),
                  X = x2),
  robust_d2 = list(f = function() locfit.robust(x2, y2, alpha = 0.7, deg = 2,
                                                 kern = "tricube", kt = "sph"),
                   X = x2)
)

timing <- character(0)
for (nm in names(cases)) {
  cs <- cases[[nm]]
  fit <- cs$f()
  wr_vec(paste0(nm, "_fitted"), fitted(fit))
  wr_vec(paste0(nm, "_se"), predict(fit, newdata = cs$X, se.fit = TRUE)$se.fit)
  wr_mat(paste0(nm, "_eva"), fit$eva$coef)
  wr_vec(paste0(nm, "_xev"), fit$eva$xev)
  wr_vec(paste0(nm, "_dp"), fit$dp[c("lk", "df1", "df2", "rv", "rsc")])
  timing <- c(timing, sprintf("%s,%.17g", nm, timed_ms(cs$f)))
  cat(nm, "vertices:", nrow(fit$eva$coef), "\n")
}

lfit <- lscv(dsamp)
wr_vec("lscv_default", as.numeric(lfit))
timing <- c(timing, sprintf("lscv,%.17g", timed_ms(function() lscv(dsamp))))
cat("lscv(dsamp):", as.numeric(lfit), "\n")

writeLines(timing, file.path(outdir, "r_timing_default.csv"))
print(timing)
