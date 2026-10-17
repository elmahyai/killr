suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
collect <- function(g) c(g$nodes, g$weights)
one <- function() {
  example <- gauss.quad(10, "laguerre", alpha = 5)
  c(
    collect(example),
    sum(example$weights * example$nodes) / gamma(6),
    collect(gauss.quad(5, "legendre")),
    collect(gauss.quad(5, "chebyshev1")),
    collect(gauss.quad(5, "chebyshev2")),
    collect(gauss.quad(5, "hermite")),
    collect(gauss.quad(5, "jacobi", alpha = 5, beta = 1.1)),
    collect(gauss.quad(5, "lag", alpha = 5)),
    length(gauss.quad(0)$nodes),
    collect(gauss.quad(1)),
    collect(gauss.quad(1, "laguerre", alpha = 5)),
    collect(gauss.quad(1, "jacobi", alpha = 5, beta = 1.1)),
    collect(gauss.quad(2.9))
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse=","), "\n", sep="")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
