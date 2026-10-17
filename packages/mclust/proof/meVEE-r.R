suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
n <- 60L
p <- 3L
K <- 3L
x <- matrix(0, n, p)
for (i in 1:n) for (j in 1:p) x[i, j] <- sin(0.37 * i + 1.3 * j) + 0.4 * cos(0.11 * i * j) + 0.05 * i / n * j
z <- matrix(0, n, K)
for (i in 1:n) {
  r <- 0.2 + ((i * (2:4) * 5) %% 7) / 7
  z[i, ] <- r / sum(r)
}
one <- function() {
  out <- mclust:::meVEE(x, z)
  c(attr(out, "returnCode"), out$loglik, out$parameters$pro,
    as.numeric(out$parameters$mean), out$parameters$variance$scale,
    out$parameters$variance$shape, as.numeric(out$parameters$variance$orientation),
    as.numeric(out$parameters$variance$sigma), as.numeric(out$z),
    as.numeric(attr(out, "info")), as.numeric(attr(attr(out, "info"), "inner")))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
