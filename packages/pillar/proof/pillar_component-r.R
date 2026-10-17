.libPaths(c(path.expand("~/R/library"), .libPaths()))
options(cli.num_colors = 8, cli.unicode = TRUE)
suppressPackageStartupMessages(library(pillar))
options(pillar.bold = FALSE, pillar.min_title_chars = 20, pillar.subtle = TRUE)

one <- function() {
  title <- pillar_component(new_pillar_title("letters"))
  kind <- pillar_component(new_pillar_type(letters))
  list(
    title_width = attr(title, "width"),
    title_min_width = attr(title, "min_width"),
    type_width = attr(kind, "width"),
    type_min_width = attr(kind, "min_width")
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
