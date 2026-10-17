.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
if (packageDescription("mix")$Version != "1.0-13") stop("expected mix 1.0-13")

# Fixed inputs: the stlouis data set of mix 1.0-13, with G, D1 and D2 categorical, and
# the unrestricted EM estimate. One call is getparam.mix with corr = FALSE and then with
# corr = TRUE. Setup is outside the timing.
data("stlouis", package = "mix", envir = environment())
s <- mix::prelim.mix(stlouis, p = 3)
th_em <- mix::em.mix(s, showits = FALSE)

num <- function(v) {
  v <- as.numeric(v)
  v[is.na(v)] <- -999999
  v
}

one <- function() {
  a <- mix::getparam.mix(s, th_em)
  b <- mix::getparam.mix(s, th_em, corr = TRUE)
  c(num(a$pi), num(a$mu), num(a$sigma), num(b$pi), num(b$mu), num(b$sdv), num(b$r))
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
