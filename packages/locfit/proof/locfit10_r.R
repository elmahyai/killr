# Proof (R side) for the ten locfit functions: lfmarg, locfit, locfit.censor,
# locfit.matrix, locfit.quasi, locfit.raw, locfit.robust, lp, lscv, lscv.exact.
#
# Reference: locfit 1.5-9.12 installed at /tmp/locfit-rlib. Install it once with
#   R CMD INSTALL --library=/tmp/locfit-rlib cran/contrib/locfit_1.5-9.12.tar.gz
# Run from the repository root:
#   Rscript packages/locfit/proof/locfit10_r.R
#
# Writes packages/locfit/docs/output/locfit_ref/:
#   in_*.csv        the fixed inputs (read by the Python proofs)
#   <case>.csv      R outputs, one row per line, %.17g
#   r_timing.csv    median ms per call: 20 samples of a 20-call loop, Sys.time()

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
suppressPackageStartupMessages(library(locfit, lib.loc = lib))
stopifnot(as.character(packageVersion("locfit")) == "1.5.9.12")

refdir <- "packages/locfit/docs/output/locfit_ref"
dir.create(refdir, recursive = TRUE, showWarnings = FALSE)

wr <- function(name, v) {
  m <- as.matrix(v)
  storage.mode(m) <- "double"
  lines <- apply(m, 1, function(r) paste(sprintf("%.17g", r), collapse = ","))
  writeLines(lines, file.path(refdir, paste0(name, ".csv")))
}

timed_ms <- function(f) {
  f()  # one untimed call
  s <- numeric(20)
  for (k in 1:20) {
    t0 <- Sys.time()
    for (j in 1:20) f()
    s[k] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000 / 20
  }
  median(s)
}

# ---- fixed inputs -------------------------------------------------------
set.seed(20241017)
n1 <- 150
x1 <- runif(n1)
y1 <- sin(2 * pi * x1) + rnorm(n1, sd = 0.2)
w1 <- runif(n1, 0.5, 1.5)
b1 <- rep(0.05, n1)
cens1 <- as.numeric(runif(n1) < 0.2)
x1m <- matrix(x1, ncol = 1)
n2 <- 100
x2 <- cbind(runif(n2), runif(n2))
y2 <- sin(3 * x2[, 1]) + x2[, 2]^2 + rnorm(n2, sd = 0.1)
xev1 <- seq(0, 1, length.out = 25)
dsamp <- rnorm(150)
xa <- x1[1:20]
xb <- x1[21:40]
ev_data <- list(type = "data", xev = 0, mg = 0, cut = 0, ll = 0, ur = 0)
df1 <- data.frame(x = x1, y = y1)
df2 <- data.frame(x1 = x2[, 1], x2 = x2[, 2], y = y2)

wr("in_x1", x1m); wr("in_y1", y1); wr("in_w1", w1); wr("in_b1", b1)
wr("in_cens1", cens1); wr("in_x2", x2); wr("in_y2", y2); wr("in_xev1", xev1)
wr("in_dsamp", dsamp); wr("in_xa", xa); wr("in_xb", xb)

# A fit's reference: eva$coef (R's 11 columns) and the dp summaries.
rec <- function(name, fit) {
  wr(paste0(name, "_coef"), fit$eva$coef)
  wr(paste0(name, "_dp"), fit$dp[c("lk", "df1", "df2", "rv", "rsc")])
}

# ---- lfmarg -------------------------------------------------------------
lf1 <- lfmarg(c(0, 1, 2, 3), m = c(5, 4))
lf2 <- lfmarg(list(mi = c(d = 2), box = c(-1, 0, 1, 2)), m = c(3, 6))
wr("lfmarg_1a", lf1[[1]]); wr("lfmarg_1b", lf1[[2]])
wr("lfmarg_2a", lf2[[1]]); wr("lfmarg_2b", lf2[[2]])

# ---- lp -----------------------------------------------------------------
lp1 <- lp(xa, xb)
lp2 <- lp(xa, nn = 0.4, h = 0.1, adpen = 2, deg = 1)
wr("lp_1_x", matrix(as.numeric(lp1), nrow = nrow(lp1)))
wr("lp_1_alpha", attr(lp1, "alpha")); wr("lp_1_deg", attr(lp1, "deg"))
wr("lp_2_x", matrix(as.numeric(lp2), nrow = nrow(lp2)))
wr("lp_2_alpha", attr(lp2, "alpha")); wr("lp_2_deg", attr(lp2, "deg"))

# ---- locfit.raw ---------------------------------------------------------
rawA <- function() locfit.raw(x1m, y1, alpha = 0.7, deg = 2, kern = "tricube", kt = "sph", ev = ev_data)
rawB <- function() locfit.raw(x1m, y1, alpha = 0.7, deg = 2, kern = "tricube", kt = "sph", ev = xev1)
rawC <- function() locfit.raw(x1m, y1, weights = w1, base = b1, alpha = 0.5, deg = 2, kern = "tricube", kt = "sph", ev = ev_data)
rawD <- function() locfit.raw(x2, y2, alpha = 0.5, deg = 1, kern = "tricube", kt = "prod", ev = ev_data)
rec("raw_A", rawA()); rec("raw_B", rawB()); rec("raw_C", rawC()); rec("raw_D", rawD())

# ---- locfit (formula front end) ----------------------------------------
F1 <- function() locfit(y ~ x, data = df1, alpha = 0.7, deg = 2, kern = "tricube", kt = "sph", ev = xev1)
F2 <- function() locfit(y ~ x1 + x2, data = df2, alpha = 0.5, deg = 1, kern = "tricube", kt = "prod", ev = ev_data)
rec("locfit_F1", F1()); rec("locfit_F2", F2())

# ---- locfit.matrix ------------------------------------------------------
fitM1 <- rawC()
M1 <- function() locfit.matrix(fitM1, data = NULL)
mm <- M1()
wr("matrix_M1_x", mm$x); wr("matrix_M1_y", mm$y); wr("matrix_M1_w", mm$w)
wr("matrix_M1_sc", mm$sc); wr("matrix_M1_ce", mm$ce); wr("matrix_M1_base", mm$base)

# ---- locfit.censor, locfit.quasi, locfit.robust (need fitted values) ----
C1 <- function() locfit.censor(x1m, y1, cens = cens1, alpha = 0.7, deg = 2, kern = "tricube", kt = "sph", ev = ev_data)
Q1 <- function() locfit.quasi(x1m, y1, alpha = 0.7, deg = 2, kern = "tricube", kt = "sph", ev = ev_data)
R1 <- function() locfit.robust(x1m, y1, alpha = 0.7, deg = 2, kern = "tricube", kt = "sph", ev = ev_data)
rec("censor_C1", C1()); rec("quasi_Q1", Q1()); rec("robust_R1", R1())

# ---- lscv, lscv.exact ---------------------------------------------------
L1 <- function() lscv(dsamp)
L2 <- function() lscv.exact(dsamp, h = 0.3)
wr("lscv_L1", as.numeric(L1()))
wr("lscv_exact_L2", as.numeric(L2()))

# ---- timing (representative call per function) --------------------------
tm <- c(
  lfmarg = timed_ms(function() lfmarg(c(0, 1, 2, 3), m = c(5, 4))),
  lp = timed_ms(function() lp(xa, xb)),
  locfit_raw = timed_ms(rawA),
  locfit = timed_ms(F1),
  locfit_matrix = timed_ms(M1),
  locfit_censor = timed_ms(C1),
  locfit_quasi = timed_ms(Q1),
  locfit_robust = timed_ms(R1),
  lscv = timed_ms(L1),
  lscv_exact = timed_ms(L2)
)
writeLines(paste0(names(tm), ",", sprintf("%.17g", tm)), file.path(refdir, "r_timing.csv"))
print(tm)
