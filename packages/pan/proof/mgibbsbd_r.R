# Proof, R side for mgibbsbd (the Fortran routine of pan 2.0 that pan.bd() calls). Runs the
# installed pan 2.0 pan.bd() on the fixed fixture and writes the chains, the final state, and
# the timings for mgibbsbd_py.py to compare.
#
# Usage:  PAN_RLIB=/tmp/pan_rlib Rscript packages/pan/proof/mgibbsbd_r.R
# One untimed call, then the median of 20 timed calls (Sys.time()).

lib <- Sys.getenv("PAN_RLIB", "/tmp/pan_rlib")
suppressPackageStartupMessages(library(pan, lib.loc = lib))
stopifnot(as.character(packageVersion("pan", lib.loc = lib)) == "2.0")

script_arg <- grep("^--file=", commandArgs(FALSE), value = TRUE)
here <- dirname(normalizePath(sub("^--file=", "", script_arg)))
fx <- file.path(here, "fixture")
out_dir <- normalizePath(file.path(here, "..", "docs", "output"), mustWork = FALSE)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

subj <- as.integer(scan(file.path(fx, "subj.csv"), what = integer(), quiet = TRUE))
pred <- as.matrix(read.csv(file.path(fx, "pred.csv"), header = FALSE))
y <- as.matrix(read.csv(file.path(fx, "y.csv"), header = FALSE, na.strings = "NA"))

seed <- 20261017L
iter <- 200L
xcol <- 1:3
zcol <- 1:2
r <- ncol(y)
q <- length(zcol)

# Priors: identity scale matrices, a = 3, c = 3 for each response. The same values as
# mgibbsbd_py.py.
prior <- list(
  a = 3,
  Binv = diag(r),
  c = rep(3, r),
  Dinv = array(c(diag(q), diag(q)), c(q, q, r))
)

run_once <- function() pan.bd(y, subj, pred, xcol, zcol, prior, seed, iter = iter)

chain <- run_once()  # untimed
times <- numeric(20)
for (k in seq_len(20)) {
  t0 <- Sys.time()
  invisible(run_once())
  times[k] <- as.numeric(Sys.time() - t0, units = "secs")
}

blocks <- list(
  betas = chain$beta, sigmas = chain$sigma, psis = chain$psi, y = chain$y,
  last_beta = chain$last$beta, last_sigma = chain$last$sigma,
  last_psi = chain$last$psi, last_y = chain$last$y
)
con <- file(file.path(out_dir, "r_mgibbsbd.txt"), "w")
for (nm in names(blocks)) {
  x <- blocks[[nm]]
  d <- dim(x)
  if (is.null(d)) d <- length(x)
  cat(sprintf("BLOCK %s %s\n", nm, paste(d, collapse = ",")), file = con)
  cat(sprintf("%.17g\n", as.vector(x)), file = con, sep = "")
}
cat(sprintf("TIMES %s\n", paste(sprintf("%.9g", times), collapse = " ")), file = con)
cat(sprintf("MEDIAN %.9g\n", median(times)), file = con)
close(con)

cat(sprintf(
  "R pan.bd() = mgibbsbd (pan %s): median of 20 = %.6f s; untimed call written to r_mgibbsbd.txt\n",
  as.character(packageVersion("pan", lib.loc = lib)), median(times)
))
