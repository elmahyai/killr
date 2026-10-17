suppressPackageStartupMessages(library(pwr))
one <- function() {
  P0 <- rep(1/4, 4)
  P1 <- c(0.375, rep((1 - 0.375)/3, 3))
  ES.w1(P0, P1)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
if (is.character(value)) cat(value, "\n", sep="") else cat(sprintf("%.17g\n", value))
cat(sprintf("%.17g\n", median(elapsed) * 1000))
