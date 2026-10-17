suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
n <- 40
p <- 3
G <- 3
i <- seq_len(n)
x <- cbind(sin(0.7 * i), 0.7 * cos(1.3 * i) + 0.1 * i / n, sin(0.4 * i + 1) - 0.5 * i / n)
mu <- matrix(c(-0.5, 0.2, 0.1, 0.4, -0.3, 0.6, 0.0, 0.9, -0.8), p, G, byrow = TRUE)
U <- array(0, c(p, p, G))
for (g in 1:G) {
  M <- diag(c(1.0, 0.8, 1.2) + 0.1 * g)
  M[1, 2] <- 0.3 * g
  M[1, 3] <- -0.2
  M[2, 3] <- 0.25 / g
  U[, , g] <- M
}
pro3 <- c(0.3, 0.45, 0.25)
pro4 <- c(0.2, 0.3, 0.3, 0.2)
pars <- function(pro) list(pro = pro, mean = mu, variance = list(cholsigma = U))
one <- function() {
  a <- estepVVV(x, pars(pro3))
  b <- estepVVV(x, pars(pro4))
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
