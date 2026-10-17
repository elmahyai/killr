suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
i <- 1:12
x <- cbind(sin(i), 0.7 * cos(i) + 0.1 * i)
mu <- matrix(c(0.2, 1.1, -0.4, 0.9), 2, 2)
O <- matrix(c(cos(pi / 6), sin(pi / 6), -sin(pi / 6), cos(pi / 6)), 2, 2)
pars <- function(pro, scale, shape) {
  list(pro = pro, mean = mu, variance = list(scale = scale, shape = shape, orientation = O))
}
one <- function() {
  a <- estepVVE(x, pars(c(0.4, 0.6), c(1.3, 0.7), matrix(c(1.5, 0.6, 0.8, 1.4), 2, 2)))
  b <- estepVVE(x, pars(c(0.3, 0.45, 0.25), c(1.3, 0.7), matrix(c(1.5, 0.6, 0.8, 1.4), 2, 2)))
  c(as.vector(a$z), a$loglik, as.vector(b$z), b$loglik)
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
