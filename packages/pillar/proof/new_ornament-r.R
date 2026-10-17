.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(pillar))
one <- function() {
  o <- new_ornament(c("abc", "de"), align = "right")
  list(
    text = paste(capture.output(print(o)), collapse = "\n"),
    format5 = format(o, width = 5),
    align = attr(o, "align", exact = TRUE),
    width = attr(o, "width", exact = TRUE)
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
