suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
one <- function() {
  f <- Digamma()
  f2 <- Digamma(link = 2)
  mus <- exp(seq(log(0.05), log(50), length.out = 40))
  y <- mus * 1.1
  eta <- f$linkfun(mus)
  c(
    as.numeric(f$linkinv(eta)),
    as.numeric(f$mu.eta(eta)),
    as.numeric(f$variance(mus)),
    as.numeric(f$dev.resids(y, mus, 1)),
    as.integer(f$validmu(mus)),
    as.integer(f$valideta(eta)),
    as.numeric(f2$linkfun(mus[c(1, 2, 3)]))
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
