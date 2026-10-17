.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(zoo))
stopifnot(packageVersion("zoo") == "1.9-1")
z <- zoo(cbind(a = c(1.5, 3.5, 5.25), b = c(2.25, 4.75, 6.125)), c(1, 2, 3))
path <- tempfile()
one <- function() {
  write.zoo(z, path)
  readChar(path, file.info(path)$size)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
esc <- function(s) {
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s
}
cat(sprintf("{\"value\":\"%s\",\"median_ms\":%.17g}\n", esc(value), median(elapsed) * 1000))
