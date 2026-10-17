suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
n <- 60L
p <- 3L
x <- matrix(0, n, p)
for (i in 1:n) for (j in 1:p) x[i, j] <- sin(0.37 * i + 1.3 * j) + 0.4 * cos(0.11 * i * j) + 0.05 * i / n * j
mu <- matrix(c(0.1, -0.2, 0.3, 0.5, 0.4, -0.1), p, 2)
a <- pi / 6
b <- pi / 5
Rz <- matrix(c(cos(a), sin(a), 0, -sin(a), cos(a), 0, 0, 0, 1), 3, 3)
Rx <- matrix(c(1, 0, 0, 0, cos(b), sin(b), 0, -sin(b), cos(b)), 3, 3)
O <- Rz %*% Rx
pars <- function(pro, scale, shape, Vinv = NULL) {
  out <- list(pro = pro, mean = mu, variance = list(scale = scale, shape = shape, orientation = O))
  if (!is.null(Vinv)) out$Vinv <- Vinv
  out
}
flat_out <- function(out) {
  v <- out$parameters$variance
  c(attr(out, "returnCode"), out$loglik, out$parameters$pro,
    as.numeric(out$parameters$mean), v$scale, v$shape, as.numeric(v$orientation),
    as.numeric(v$sigma), as.numeric(out$z),
    as.numeric(attr(out, "info")), as.numeric(attr(attr(out, "info"), "inner")))
}
one <- function() {
  a <- emEVE(x, pars(c(0.4, 0.6), 0.9, matrix(c(1.5, 0.6, 0.9, 0.8, 1.4, 1.1), p, 2)))
  b <- emEVE(x, pars(c(0.3, 0.45, 0.25), 0.9, matrix(c(1.5, 0.6, 0.9, 0.8, 1.4, 1.1), p, 2), Vinv = 0.15))
  c(flat_out(a), flat_out(b))
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
