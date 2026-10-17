suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

one <- function() {
  z <- matrix(c(0.7, 0.3, 0.2, 0.8, 0.6, 0.4), nrow = 3, ncol = 2, byrow = TRUE)
  class <- c(1L, 2L, 1L)
  BrierScore(z, class)
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
