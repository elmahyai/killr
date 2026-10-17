suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

one <- function() {
  a <- rep(1:3, 3)
  b <- rep(c("A", "B", "C"), 3)
  v1 <- adjustedRandIndex(a, b)
  set.seed(42)
  a2 <- sample(1:3, 9, replace = TRUE)
  b2 <- sample(c("A", "B", "C"), 9, replace = TRUE)
  v2 <- adjustedRandIndex(a2, b2)
  a3 <- rep(1:3, 4)
  b3 <- rep(c("A", "B", "C", "D"), 3)
  v3 <- adjustedRandIndex(a3, b3)
  c(v1, v2, v3)
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
