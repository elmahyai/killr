suppressPackageStartupMessages(library(yaml))
path <- tempfile()
writeLines(c("flag: y", "oct: 015"), path)
one <- function() {
  value <- read_yaml(path)
  paste(value$flag, value$oct, sep = ",")
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
