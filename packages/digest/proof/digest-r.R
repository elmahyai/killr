suppressPackageStartupMessages(library(digest))
obj <- list(LETTERS, data.frame(a = letters[1:5], b = matrix(1:10, ncol = 2)))
one <- function() digest(obj)
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%s\n%.17g\n", value, median(elapsed) * 1000))
