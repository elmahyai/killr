.libPaths(c(path.expand("~/R/library"), .libPaths()))
options(cli.num_colors = 8, cli.unicode = TRUE)
suppressPackageStartupMessages(library(pillar))
options(pillar.bold = FALSE, pillar.subtle = TRUE)

one <- function() {
  kind <- new_pillar_type(letters)
  list(
    chr = format(new_pillar_type("a")),
    fct = format(new_pillar_type(factor("a"))),
    width = attr(kind, "width"),
    min_width = attr(kind, "min_width")
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
