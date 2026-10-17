suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
n <- 40
p <- 3
G <- 3
i <- seq_len(n)
x <- cbind(sin(0.7 * i), 0.7 * cos(1.3 * i) + 0.1 * i / n, sin(0.4 * i + 1) - 0.5 * i / n)
mu <- matrix(c(-0.5, 0.2, 0.1, 0.4, -0.3, 0.6, 0.0, 0.9, -0.8), p, G, byrow = TRUE)
pro <- c(0.3, 0.45, 0.25)
sig <- c(0.6, 1.4, 0.9)
pars <- list(pro = pro, mean = mu, variance = list(sigmasq = sig))
one <- function() {
  a <- cdensVII(x, logarithm = TRUE, parameters = pars)
  b <- cdensVII(x, logarithm = FALSE, parameters = pars)
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
