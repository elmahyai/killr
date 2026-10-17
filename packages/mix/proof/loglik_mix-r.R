.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
if (packageDescription("mix")$Version != "1.0-13") stop("expected mix 1.0-13")

# Fixed inputs: the stlouis data set of mix 1.0-13, with G, D1 and D2 categorical. The
# unrestricted EM estimate and the ECM estimate of the alternative model (margins and
# design as in tests/mix.R) are the two parameter values. Setup is outside the timing.
data("stlouis", package = "mix", envir = environment())
s <- mix::prelim.mix(stlouis, p = 3)
th_em <- mix::em.mix(s, showits = FALSE)
margins <- c(1, 2, 0, 2, 3, 0, 1, 3)
intercept <- rep(1, 12)
d1 <- c(-1, -1, -1, 1, 1, 1, -1, -1, -1, 1, 1, 1)
d2 <- c(-1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1)
glin <- c(-1, 0, 1, -1, 0, 1, -1, 0, 1, -1, 0, 1)
design <- cbind(intercept, d1, d2, d1d2 = d1 * d2, glin)
th_ecm <- mix::ecm.mix(s, margins, design, showits = FALSE)

num <- function(v) {
  v <- as.numeric(v)
  v[is.na(v)] <- -999999
  v
}

one <- function() {
  c(mix::loglik.mix(s, th_em), mix::loglik.mix(s, th_ecm))
}

value <- one()
elapsed <- numeric(20)
for (k in 1:20) {
  t0 <- as.numeric(Sys.time())
  invisible(one())
  elapsed[k] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", num(value)), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
