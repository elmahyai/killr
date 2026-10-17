.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
if (packageDescription("mix")$Version != "1.0-13") stop("expected mix 1.0-13")

# Fixed inputs: the stlouis data set of mix 1.0-13 and the alternative ECM model of
# tests/mix.R, as in ecm_mix-r.R. The start is that ECM fit. One call seeds the
# generator with 4242, as the other proofs do, then takes 100 steps of dabipf.mix.
# Setup is outside the timing.
data("stlouis", package = "mix", envir = environment())
s <- mix::prelim.mix(stlouis, p = 3)
margins <- c(1, 2, 0, 2, 3, 0, 1, 3)
intercept <- rep(1, 12)
d1 <- c(-1, -1, -1, 1, 1, 1, -1, -1, -1, 1, 1, 1)
d2 <- c(-1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1)
glin <- c(-1, 0, 1, -1, 0, 1, -1, 0, 1, -1, 0, 1)
design <- cbind(intercept, d1, d2, d1d2 = d1 * d2, glin)
start <- mix::ecm.mix(s, margins, design, showits = FALSE)

num <- function(v) {
  v <- as.numeric(v)
  v[is.na(v)] <- -999999
  v
}

one <- function() {
  mix::rngseed(4242)
  da <- mix::dabipf.mix(s, margins, design, start, steps = 100, showits = FALSE)
  c(num(da$sigma), num(da$mu), num(da$pi))
}

value <- one()
elapsed <- numeric(20)
for (k in 1:20) {
  t0 <- as.numeric(Sys.time())
  invisible(one())
  elapsed[k] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
