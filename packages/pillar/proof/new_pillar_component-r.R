.libPaths(c(path.expand("~/R/library"), .libPaths()))
options(cli.num_colors = 8, cli.unicode = TRUE)
suppressPackageStartupMessages(library(pillar))

one <- function() {
  x <- new_pillar_component(list(letters[1:3]), width = 1)
  y <- new_pillar_component(list(letters[1:3]), width = 5, min_width = 2)
  list(
    width = attr(x, "width"),
    min_width = attr(x, "min_width"),
    values = x[[1]],
    width2 = attr(y, "width"),
    min2 = attr(y, "min_width")
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
