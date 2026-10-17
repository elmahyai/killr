.libPaths(c(path.expand("~/R/library"), .libPaths()))
options(cli.num_colors = 8, cli.unicode = TRUE)
suppressPackageStartupMessages(library(pillar))
options(pillar.bold = FALSE, pillar.subtle = TRUE, pillar.min_title_chars = 20)

one <- function() {
  list(
    trees = format(new_pillar_title(names(trees))),
    letters = format(new_pillar_title("letters")),
    trunc = format(new_pillar_title(c("hello", "hi")), width = 4),
    empty = format(new_pillar_title(NULL))
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
