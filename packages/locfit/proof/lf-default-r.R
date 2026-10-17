# R reference for lf() on R's default ev = rbox() (adaptive kd-tree spec), d = 1 and d = 2.
# locfit 1.5-9.12. Run from the repository root:
#   Rscript --slave packages/locfit/proof/lf-default-r.R
#
# R's lf() only records its arguments as attributes of cbind(...). The default
# ev = rbox() is a list (type "tree", cut 0.8). The kd-tree is used when the term
# is fitted, so the chain cases below pass attr(lf(x), "ev") to locfit.raw and
# compare the fitted values with R on the same tree.
#
# Writes packages/locfit/docs/output/lf_default_r/:
#   in_x1.csv, in_y1.csv, in_x2.csv, in_y2.csv     fixed inputs (same seeds as locfit-default-r.R)
#   <case>_x.csv        the covariate matrix (lf's cbind(...)), one row per point
#   <case>_num.csv      alpha, deg, scale, maxk
#   <case>_ev.csv       ev$xev, ev$mg, ev$cut, ev$ll, ev$ur (numeric fields of the ev list)
#   <case>_ev_type.txt  ev$type
#   <case>_fitted.csv   fitted(locfit.raw(x, y, ev = attr(lf(x), "ev"))), chain cases only
#   timing.csv          case,ms: median over 20 timed calls (one untimed call first)
#
# Timing: one untimed call, then the median of 20 timed calls. Sys.time().

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
suppressPackageStartupMessages(library(locfit, lib.loc = lib))
stopifnot(as.character(packageVersion("locfit")) == "1.5.9.12")

outdir <- "packages/locfit/docs/output/lf_default_r"
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

# Fixed inputs: the same seeds and draws as locfit-default-r.R.
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

# Cases. Each closure returns the lf term (or the chain fit) so timing covers the call.
lf_d1 <- function() lf(x1)
lf_d2 <- function() lf(x2[, 1], x2[, 2])
lf_d1_dat <- function() lf(x1, alpha = 0.5, deg = 1, scale = 2, kern = "gauss",
                           maxk = 50, ev = dat())
lf_d2_dat <- function() lf(x2[, 1], x2[, 2], alpha = 0.5, deg = 1, scale = 2,
                           kern = "gauss", maxk = 50, ev = dat())
chain_d1 <- function() locfit.raw(x1, y1, ev = attr(lf(x1), "ev"))
chain_d2 <- function() locfit.raw(x2, y2, ev = attr(lf(x2[, 1], x2[, 2]), "ev"))

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

term_cases <- list(lf_d1 = lf_d1, lf_d2 = lf_d2, lf_d1_dat = lf_d1_dat, lf_d2_dat = lf_d2_dat)
timing <- character(0)
for (nm in names(term_cases)) {
  f <- term_cases[[nm]]
  t <- f()
  wr_mat(paste0(nm, "_x"), unclass(t))
  wr_vec(paste0(nm, "_num"), c(attr(t, "alpha"), attr(t, "deg"), attr(t, "scale"), attr(t, "maxk")))
  ev <- attr(t, "ev")
  wr_vec(paste0(nm, "_ev"), c(ev$xev, ev$mg, ev$cut, ev$ll, ev$ur))
  writeLines(ev$type, file.path(outdir, paste0(nm, "_ev_type.txt")))
  timing <- c(timing, sprintf("%s,%.17g", nm, time_ms(f)))
}

for (nm in c("chain_d1", "chain_d2")) {
  f <- get(nm)
  fit <- f()
  wr_vec(paste0(nm, "_fitted"), fitted(fit))
  timing <- c(timing, sprintf("%s,%.17g", nm, time_ms(f)))
}

writeLines(timing, file.path(outdir, "timing.csv"))
print(timing)
