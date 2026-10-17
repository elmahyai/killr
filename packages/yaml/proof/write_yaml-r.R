suppressPackageStartupMessages(library(yaml))
path <- tempfile()
one <- function() {
  write_yaml(list(foo = 1:3), path)
  paste(readLines(path), collapse = "|")
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
