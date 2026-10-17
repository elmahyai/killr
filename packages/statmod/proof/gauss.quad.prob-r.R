suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

collect <- function(g) c(g$nodes, g$weights)

one <- function() {
  normal <- gauss.quad.prob(10, "normal")
  gamma_out <- gauss.quad.prob(32, "gamma", alpha = 5)
  c(
    sum(normal$weights * normal$nodes^4),
    sum(gamma_out$weights * log(gamma_out$nodes)),
    collect(gauss.quad.prob(5, "uniform", l = 0.2, u = 1.8)),
    collect(gauss.quad.prob(5, "beta1")),
    collect(gauss.quad.prob(5, "beta2")),
    collect(gauss.quad.prob(5, "beta", alpha = 3, beta = 2)),
    collect(gauss.quad.prob(5, "beta", alpha = 0.5, beta = 0.5)),
    collect(gauss.quad.prob(5, "beta", alpha = 1.5, beta = 1.5)),
    collect(gauss.quad.prob(5, "normal", mu = 2, sigma = 3)),
    collect(gauss.quad.prob(5, "gamma", alpha = 2, beta = 0.5)),
    length(gauss.quad.prob(0)$nodes),
    collect(gauss.quad.prob(1, "uniform", l = 1, u = 5)),
    collect(gauss.quad.prob(1, "normal", mu = 7)),
    collect(gauss.quad.prob(1, "gamma", alpha = 3, beta = 2)),
    collect(gauss.quad.prob(1, "beta", alpha = 2, beta = 3)),
    collect(gauss.quad.prob(2.9))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
