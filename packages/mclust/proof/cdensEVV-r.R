suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
n <- 40
p <- 3
G <- 3
i <- seq_len(n)
x <- cbind(sin(0.7 * i), 0.7 * cos(1.3 * i) + 0.1 * i / n, sin(0.4 * i + 1) - 0.5 * i / n)
mu <- matrix(c(-0.5, 0.2, 0.1, 0.4, -0.3, 0.6, 0.0, 0.9, -0.8), p, G, byrow = TRUE)
pro <- c(0.3, 0.45, 0.25)
shM <- matrix(c(1.5, 0.7, 1.1, 0.9, 1.2, 0.8, 1.0, 0.6, 1.3), p, G)
orient <- function(k) {
  a <- 0.3 * k
  b <- 0.5 * k
  Rz <- matrix(c(cos(a), sin(a), 0, -sin(a), cos(a), 0, 0, 0, 1), 3, 3)
  Rx <- matrix(c(1, 0, 0, 0, cos(b), sin(b), 0, -sin(b), cos(b)), 3, 3)
  Rz %*% Rx
}
O <- array(0, c(p, p, G))
for (k in 1:G) O[, , k] <- orient(k)
pars <- list(pro = pro, mean = mu, variance = list(scale = 1.1, shape = shM, orientation = O))
one <- function() {
  a <- cdensEVV(x, logarithm = TRUE, parameters = pars)
  b <- cdensEVV(x, logarithm = FALSE, parameters = pars)
  c(as.vector(a), as.vector(b))
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
