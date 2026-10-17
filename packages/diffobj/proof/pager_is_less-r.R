.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(diffobj))
one <- function() pager_is_less()

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(if (isTRUE(value)) "TRUE" else "FALSE", "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
