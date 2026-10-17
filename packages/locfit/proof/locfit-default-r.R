# R reference for locfit() and locfit.raw() on R's default ev = rbox() (kd-tree).
# locfit 1.5-9.12. Run from the repository root:
#   Rscript --slave packages/locfit/proof/locfit-default-r.R
#
# Writes packages/locfit/docs/output/locfit_default_r/:
#   in_x1.csv, in_y1.csv, in_x2.csv, in_y2.csv   fixed inputs (read by the Python proof)
#   <case>_fitted.csv   fitted(fit) at the data
#   <case>_se.csv       predict(fit, newdata = x, se.fit = TRUE)$se.fit at the data
#   <case>_eva.csv      fit$eva$coef without the trailing deg column (one row per vertex)
#   <case>_xev.csv      fit$eva$xev, the vertices (flat)
#   <case>_dp.csv       lk, df1, df2, rv, rsc
#   timing.csv          case,ms: median over 20 timed calls (one untimed call first)

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
suppressPackageStartupMessages(library(locfit, lib.loc = lib))
stopifnot(as.character(packageVersion("locfit")) == "1.5.9.12")

outdir <- "packages/locfit/docs/output/locfit_default_r"
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

# Fixed inputs. Fixed seeds; the Python proof reads these files, never R.
set.seed(11)
n1 <- 150
x1 <- matrix(runif(n1), ncol = 1)
y1 <- sin(2 * pi * x1[, 1]) + 0.2 * rnorm(n1)
set.seed(12)
n2 <- 120
x2 <- cbind(runif(n2), runif(n2))
y2 <- sin(2 * pi * x2[, 1]) * x2[, 2] + 0.2 * rnorm(n2)

wr_vec <- function(name, v)
  writeLines(sprintf("%.17g", as.numeric(v)), file.path(outdir, paste0(name, ".csv")))
wr_mat <- function(name, m) {
  m <- as.matrix(m)
  storage.mode(m) <- "double"
  writeLines(apply(m, 1, function(r) paste(sprintf("%.17g", r), collapse = ",")),
             file.path(outdir, paste0(name, ".csv")))
}
wr_vec("in_x1", x1[, 1]); wr_vec("in_y1", y1)
wr_mat("in_x2", x2);      wr_vec("in_y2", y2)

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

d1 <- data.frame(x = x1[, 1], y = y1)
d2 <- data.frame(x1 = x2[, 1], x2 = x2[, 2], y = y2)

cases <- list(
  locfit_d1 = list(f = function() locfit(y ~ x, data = d1), X = x1),
  locfit_d2 = list(f = function() locfit(y ~ x1 + x2, data = d2), X = x2),
  locfit.raw_d1 = list(f = function() locfit.raw(x1, y1), X = x1),
  locfit.raw_d2 = list(f = function() locfit.raw(x2, y2), X = x2)
)

timing <- character(0)
for (nm in names(cases)) {
  cs <- cases[[nm]]
  fit <- cs$f()
  wr_vec(paste0(nm, "_fitted"), fitted(fit))
  wr_vec(paste0(nm, "_se"), predict(fit, newdata = cs$X, se.fit = TRUE)$se.fit)
  ev <- fit$eva$coef
  wr_mat(paste0(nm, "_eva"), ev[, -ncol(ev), drop = FALSE])
  wr_vec(paste0(nm, "_xev"), fit$eva$xev)
  wr_vec(paste0(nm, "_dp"), fit$dp[c("lk", "df1", "df2", "rv", "rsc")])
  timing <- c(timing, sprintf("%s,%.17g", nm, time_ms(cs$f)))
  cat(nm, "vertices:", nrow(ev), "\n")
}
writeLines(timing, file.path(outdir, "timing.csv"))
print(timing)
