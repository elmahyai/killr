suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

one <- function() {
  x <- matrix(c(-1.2, -0.5, -2.1, -0.3, -1.0, -1.8), nrow = 2, ncol = 3)
  v <- c(0, log(0.3), log(0.7))
  logsumexp(x, v)
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
