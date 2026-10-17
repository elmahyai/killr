.libPaths(c(path.expand("~/R/library"), .libPaths()))
options(cli.unicode = TRUE)
suppressPackageStartupMessages(library(pillar))

json_str <- function(s) {
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  paste0('"', s, '"')
}

one <- function() {
  c(
    dim_desc(1:10),
    dim_desc(Titanic),
    dim_desc(NULL),
    dim_desc(trees),
    dim_desc(matrix(1:4, nrow = 2)),
    dim_desc(1:1000),
    dim_desc(data.frame(a = 1)),
    dim_desc(matrix(1:10))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(vapply(value, json_str, ""), collapse = ","),
  median(elapsed) * 1000
))
