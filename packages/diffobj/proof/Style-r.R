.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(diffobj))
options(crayon.enabled=TRUE, width=80)
one <- function() {
  tryCatch(Style(), error = function(e) conditionMessage(e))
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
