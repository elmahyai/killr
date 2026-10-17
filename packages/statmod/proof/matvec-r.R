suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
one <- function() {
  A <- matrix(1:12, 3, 4)
  rows <- rep(1:100, each = 50)
  cols <- rep(1:50, times = 100)
  M <- matrix(rows + cols / 100, 100, 50)
  v <- (1:50) / 7
  c(as.vector(matvec(A, c(1, 2, 3, 4))), as.vector(matvec(M, v)))
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
