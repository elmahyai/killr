suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

proof_matrices <- function() {
  y1 <- outer(1:50, 1:30, function(i, j) sin(i * j / 100))
  y2 <- outer(1:40, 1:30, function(i, j) cos(i * j / 100))
  y1[seq(1, length(y1), by = 7)] <- NA
  y2[seq(1, length(y2), by = 7)] <- NA
  list(y1 = y1, y2 = y2)
}

one <- function() {
  mats <- proof_matrices()
  meanT(mats$y1, mats$y2)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", as.numeric(value)))
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
