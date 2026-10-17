suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
n <- 60L
p <- 3L
x <- matrix(0, n, p)
for (i in 1:n) for (j in 1:p) x[i, j] <- sin(0.37 * i + 1.3 * j) + 0.4 * cos(0.11 * i * j) + 0.05 * i / n * j
one <- function() {
  out <- mclust:::meXII(x)
  c(attr(out, "returnCode"), out$loglik, as.numeric(out$parameters$mean),
    out$parameters$variance$sigmasq)
}
value <- one()
elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[k]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
