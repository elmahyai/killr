# Proof, R side. Runs the installed pan 2.0 R functions on the fixed fixture and
# writes the chains and the timings for the Python proof (pan_py.py) to compare.
#
# Usage:  PAN_RLIB=/tmp/pan_rlib Rscript packages/pan/proof/pan_r.R bd
#         PAN_RLIB=/tmp/pan_rlib Rscript packages/pan/proof/pan_r.R full
# "bd" runs pan.bd (mgibbsbd), "full" runs pan (mgibbs). Each kernel runs in its own
# process so the Fortran gauss state starts the same way on both sides.
# pan 2.0 is installed with: R CMD INSTALL -l /tmp/pan_rlib <unpacked pan_2.0.tar.gz>/pan

args <- commandArgs(trailingOnly = TRUE)
kernel <- args[1]
stopifnot(kernel %in% c("bd", "full"))

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
rq <- r * q

# Priors: identity scale matrices, a = 3, c = 3. The values are the same as in pan_py.py.
prior_bd <- list(
  a = 3,
  Binv = diag(r),
  c = rep(3, r),
  Dinv = array(c(diag(q), diag(q)), c(q, q, r))
)
prior_full <- list(a = 3, Binv = diag(r), c = 3, Dinv = diag(rq))

run_once <- function() {
  if (kernel == "bd") {
    pan.bd(y, subj, pred, xcol, zcol, prior_bd, seed, iter = iter)
  } else {
    pan(y, subj, pred, xcol, zcol, prior_full, seed, iter = iter)
  }
}

# One untimed call, then the median of 20 timed calls.
chain <- run_once()
times <- numeric(20)
for (k in seq_len(20)) {
  t0 <- Sys.time()
  invisible(run_once())
  times[k] <- as.numeric(Sys.time() - t0, units = "secs")
}

blocks <- list(betas = chain$beta, sigmas = chain$sigma, psis = chain$psi, y = chain$y)
con <- file(file.path(out_dir, paste0("r_", kernel, ".txt")), "w")
for (nm in names(blocks)) {
  x <- blocks[[nm]]
  cat(sprintf("BLOCK %s %s\n", nm, paste(dim(x), collapse = ",")), file = con)
  cat(sprintf("%.17g\n", as.vector(x)), file = con, sep = "")
}
cat(sprintf("TIMES %s\n", paste(sprintf("%.9g", times), collapse = " ")), file = con)
cat(sprintf("MEDIAN %.9g\n", median(times)), file = con)
close(con)

cat(sprintf(
  "R %s (pan %s, Fortran via R): median of 20 = %.6f s; untimed call written to r_%s.txt\n",
  if (kernel == "bd") "pan.bd" else "pan", as.character(packageVersion("pan", lib.loc = lib)),
  median(times), kernel
))
