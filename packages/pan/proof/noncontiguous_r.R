# Probe pan() or pan.bd() with interleaved subjects.  pan 2.0 sets m to
# length(table(subj)) but its Fortran istfin walk assumes contiguous runs.
# The child process is expected to abort with a segmentation fault; this file
# deliberately does not catch that native abort.

args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 1L, args[[1]] %in% c("mgibbs", "mgibbsbd"))
lib <- Sys.getenv("PAN_RLIB", "/tmp/pan_rlib")
suppressPackageStartupMessages(library(pan, lib.loc = lib))

fx <- file.path(dirname(normalizePath(sub("^--file=", "",
  grep("^--file=", commandArgs(FALSE), value = TRUE)))), "fixture")
subj <- scan(file.path(fx, "subj.csv"), what = integer(), quiet = TRUE)
pred <- as.matrix(read.csv(file.path(fx, "pred.csv"), header = FALSE))
y <- as.matrix(read.csv(file.path(fx, "y.csv"), header = FALSE, na.strings = "NA"))

# Preserve y/pred row order but interleave the two existing subjects.
subj <- rep(seq_len(length(unique(subj))), length.out = length(subj))
xcol <- 1:3
zcol <- 1:2
if (args[[1]] == "mgibbs") {
  prior <- list(a = 3, Binv = diag(2), c = 3, Dinv = diag(4))
  pan(y, subj, pred, xcol, zcol, prior, 20261017L, iter = 1L)
} else {
  prior <- list(a = 3, Binv = diag(2), c = rep(3, 2),
                Dinv = array(c(diag(2), diag(2)), c(2, 2, 2)))
  pan.bd(y, subj, pred, xcol, zcol, prior, 20261017L, iter = 1L)
}
