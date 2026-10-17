.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
shapeO <- get("shapeO", envir = asNamespace("mclust"))
one <- function() {
  O <- array(c(
    0.2, 0.5, 0.1,
    0.3, 0.4, 0.6,
    0.7, 0.2, 0.8,
    0.1, 0.9, 0.3,
    0.4, 0.2, 0.5,
    0.6, 0.7, 0.1
  ), dim = c(3, 3, 2))
  shape <- c(1.5, 0.5, 2)
  a <- shapeO(shape, O, transpose = FALSE)
  b <- shapeO(shape, O, transpose = TRUE)
  M <- matrix(c(0.2, 0.5, 0.1, 0.3, 0.4, 0.6, 0.7, 0.2, 0.8), 3, 3)
  c <- shapeO(shape, M, transpose = FALSE)
  c(a, b, c)
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
