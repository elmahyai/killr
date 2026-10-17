suppressPackageStartupMessages(library(yaml))
one <- function() {
  value <- yaml.load("flag: y\nclock: 1:20\n")
  paste(value$flag, value$clock, sep = ",")
}
ans <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(ans, "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
