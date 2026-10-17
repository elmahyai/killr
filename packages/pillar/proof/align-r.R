.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(pillar))
one <- function() {
  list(
    align(c("abc", "de"), align = "left"),
    align(c("abc", "de"), align = "right"),
    align(c("a", NA), align = "left"),
    align(c("a", "bb"), space = "ab")
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(
  list(value = value, median_ms = median(elapsed) * 1000),
  auto_unbox = TRUE,
  digits = 16
))
cat("\n")
