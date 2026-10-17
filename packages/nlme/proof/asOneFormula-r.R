.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  paste(
    deparse(asOneFormula(y ~ x + z | g, list(~w, ~t * sin(2 * pi)))),
    collapse = ""
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
escaped <- gsub("\\\\", "\\\\\\\\", value, fixed = TRUE)
escaped <- gsub("\"", "\\\\\"", escaped, fixed = TRUE)
cat(sprintf(
  "{\"value\":\"%s\",\"median_ms\":%.17g}\n",
  escaped,
  median(elapsed) * 1000
))
