.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(diffobj))
options(crayon.enabled=TRUE, width=80)
one <- function() {
  p <- PagerBrowser()
  mb <- if (length(p@make.blocking) == 1L && is.na(p@make.blocking)) "NA" else as.character(p@make.blocking)
  paste(class(p)[[1]], p@file.ext, mb, sep = "|")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
txt <- if (is.character(value)) paste(value, collapse = "\n") else as.character(value)
cat("VALUE\n")
cat(txt)
cat("\n<<<END>>>\n")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
