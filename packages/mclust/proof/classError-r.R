suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

flatten <- function(out) {
  c(out$errorRate, out$misclassified)
}

one <- function() {
  a <- rep(1:3, 3)
  b <- rep(c("A", "B", "C"), 3)
  v1 <- flatten(classError(a, b))
  a2 <- c(1, 1, 1, 1, 2, 2, 2, 1, 3)
  b2 <- c("C", "A", "A", "B", "B", "B", "C", "C", "A")
  v2 <- flatten(classError(a2, b2))
  class <- factor(c(5, 5, 5, 2, 5, 3, 1, 2, 1, 1), levels = 1:5)
  pred <- c(3, 5, 5, 2, 3, 3, 1, 5, 1, 1)
  v3 <- flatten(classError(pred, class))
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
