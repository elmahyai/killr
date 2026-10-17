.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
unchol <- get("unchol", envir = asNamespace("mclust"))
one <- function() {
  U <- matrix(c(2, 0, 0, 0.5, 1.5, 0, -0.3, 0.4, 1.2), 3, 3)
  L <- matrix(c(2, 0.5, -0.3, 0, 1.5, 0.4, 0, 0, 1.2), 3, 3)
  D <- diag(c(2, 3, 4))
  a <- unchol(U, upper = TRUE)
  b <- unchol(L, upper = FALSE)
  c <- suppressWarnings(unchol(U))
  d <- suppressWarnings(unchol(L))
  e <- suppressWarnings(unchol(D))
  f <- suppressWarnings(unchol(matrix(2, 1, 1)))
  g <- suppressWarnings(unchol(matrix(1.5, 1, 1)))
  c(a, b, c, d, e, f, g)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
