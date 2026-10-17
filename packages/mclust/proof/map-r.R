suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

one <- function() {
  z <- matrix(c(0.9, 0.05, 0.05, 0.1, 0.8, 0.1, 0.2, 0.2, 0.6), nrow = 3, ncol = 3, byrow = TRUE)
  as.vector(map(z))
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
