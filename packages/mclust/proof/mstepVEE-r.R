suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
i <- 1:24
x <- cbind(i / 10 + (i %% 5), ((i * i) %% 7) / 3 - i / 20, ((i * 3) %% 11) / 2 + i / 50)
zmat <- function(G) {
  raw <- sapply(1:G, function(g) 1 + ((i + 2 * g) %% 3))
  raw / rowSums(raw)
}
z2 <- zmat(2)
z3 <- zmat(3)
flat <- function(r) {
  p <- r$parameters
  as.numeric(c(p$pro, p$mean, p$variance$sigma, p$variance$scale, p$variance$shape,
               p$variance$orientation, attr(r, "returnCode"), attr(r, "info")))
}
one <- function() {
  c(flat(mclust:::mstepVEE(x, z2)), flat(mclust:::mstepVEE(x, z3)))
}
value <- one()
elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[k] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
