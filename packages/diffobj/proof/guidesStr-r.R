.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(diffobj))
options(crayon.enabled=TRUE, width=80)
one <- function() {
  txt <- c("List of 2", " $ a: num 1", " $ b:List of 1", "  ..$ c: num 2")
  g <- guidesStr(list(a = 1), txt)
  if (!length(g)) "EMPTY" else paste(g, collapse = ",")
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
