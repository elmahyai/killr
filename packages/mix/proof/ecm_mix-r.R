.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
if (packageDescription("mix")$Version != "1.0-13") stop("expected mix 1.0-13")

# Fixed inputs: the stlouis data set of mix 1.0-13, with G, D1 and D2 categorical. The
# alternative model of tests/mix.R: margins c(1,2,0,2,3,0,1,3) and the design of an
# intercept, D1, D2, D1*D2 and the linear G effect, with no starting value.
# Setup is outside the timing.
data("stlouis", package = "mix", envir = environment())
s <- mix::prelim.mix(stlouis, p = 3)
margins <- c(1, 2, 0, 2, 3, 0, 1, 3)
intercept <- rep(1, 12)
d1 <- c(-1, -1, -1, 1, 1, 1, -1, -1, -1, 1, 1, 1)
d2 <- c(-1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1)
glin <- c(-1, 0, 1, -1, 0, 1, -1, 0, 1, -1, 0, 1)
design <- cbind(intercept, d1, d2, d1d2 = d1 * d2, glin)

num <- function(v) {
  v <- as.numeric(v)
  v[is.na(v)] <- -999999
  v
}

one <- function() {
  th <- mix::ecm.mix(s, margins, design, showits = FALSE)
  c(num(th$sigma), num(th$mu), num(th$pi))
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
