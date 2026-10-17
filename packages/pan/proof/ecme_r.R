# Proof, R side for ecme(). Runs the installed pan 2.0 ecme() on the fixed fixture for
# five cases and writes the results and the timings for ecme_py.py to compare.
#
# Usage:  PAN_RLIB=/tmp/pan_rlib Rscript packages/pan/proof/ecme_r.R
# Cases: A univariate, no vmax; B univariate, vmax; C random intercept and time with
# random.effects; D random intercept and time, vmax; E random intercept and time, start.
# Each case: one untimed call, then the median of 20 timed calls (Sys.time()).

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
y <- scan(file.path(fx, "ecme_y.csv"), what = double(), quiet = TRUE)
occ <- as.integer(scan(file.path(fx, "ecme_occ.csv"), what = integer(), quiet = TRUE))
vmax <- as.matrix(read.csv(file.path(fx, "ecme_vmax.csv"), header = FALSE))

xcol <- 1:3
zcol <- 1:2
start <- list(beta = c(1.0, 0.5, 0.3), sigma2 = 1, psi = matrix(c(0.5, 0.1, 0.1, 0.5), 2, 2))

cases <- list(
  A = function() ecme(y, subj, occ, pred, xcol, zcol = NULL),
  B = function() ecme(y, subj, occ, pred, xcol, zcol = NULL, vmax = vmax),
  C = function() ecme(y, subj, occ, pred, xcol, zcol = zcol, random.effects = TRUE),
  D = function() ecme(y, subj, occ, pred, xcol, zcol = zcol, vmax = vmax),
  E = function() ecme(y, subj, occ, pred, xcol, zcol = zcol, start = start)
)

items <- c("beta", "sigma2", "psi", "converged", "iter", "loglik", "cov.beta", "bhat", "cov.b")
con <- file(file.path(out_dir, "r_ecme.txt"), "w")
medians <- numeric(length(cases))
names(medians) <- names(cases)

# The zcol = NULL branch of pan 2.0 calls prelim with zcol = 0, so mmu reads pred(., 0),
# which is memory before pred. In some runs that value is NaN and .Fortran stops with
# "NA/NaN/Inf in foreign function call". The value is never used by nopsi, so a call
# that fails is retried until one succeeds. The number of attempts is written.
attempts <- integer(length(cases))
names(attempts) <- names(cases)
run_once <- function(f) {
  # Returns the value of f() or NULL when the call stops on an error.
  val <- NULL
  ok <- tryCatch({ invisible(capture.output(val <- f())); TRUE }, error = function(e) FALSE)
  if (ok) val else NULL
}

for (case in names(cases)) {
  f <- cases[[case]]
  res <- NULL
  a <- 0L
  while (is.null(res) && a < 200L) {
    a <- a + 1L
    res <- run_once(f)
  }
  if (is.null(res)) stop(sprintf("ecme case %s failed 200 times", case))
  attempts[case] <- a
  times <- numeric(20)
  for (k in seq_len(20)) {
    el <- NA_real_
    while (is.na(el)) {
      t0 <- Sys.time()
      v <- run_once(f)
      if (!is.null(v)) el <- as.numeric(Sys.time() - t0, units = "secs")
    }
    times[k] <- el
  }
  medians[case] <- median(times)
  cat(sprintf("CASE %s\n", case), file = con)
  cat(sprintf("ATTEMPTS %d\n", a), file = con)
  for (nm in items) {
    x <- res[[nm]]
    if (is.null(x)) {
      cat(sprintf("NULL %s\n", nm), file = con)
      next
    }
    x <- as.numeric(x)
    d <- dim(res[[nm]])
    if (is.null(d)) d <- length(x)
    cat(sprintf("BLOCK %s %s\n", nm, paste(d, collapse = ",")), file = con)
    cat(sprintf("%.17g\n", x), file = con, sep = "")
  }
  cat(sprintf("TIMES %s\n", paste(sprintf("%.9g", times), collapse = " ")), file = con)
  cat(sprintf("MEDIAN %.9g\n", median(times)), file = con)
}
close(con)

cat(sprintf("R ecme (pan %s) medians of 20 (s): %s\n", as.character(packageVersion("pan", lib.loc = lib)),
            paste(sprintf("%s=%.6f", names(medians), medians), collapse = " ")))
