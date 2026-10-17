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
    type_sum(factor(letters[1:3])),
    type_sum(ordered(letters[1:3])),
    type_sum(1:10),
    type_sum(1.5),
    type_sum(TRUE),
    type_sum("a"),
    type_sum(1 + 2i),
    type_sum(as.raw(1)),
    type_sum(data.frame(a = 1)),
    type_sum(matrix(1:4, nrow = 2)),
    type_sum(Titanic),
    type_sum(Sys.Date()),
    type_sum(Sys.time()),
    type_sum(list(1, 2)),
    type_sum(mean),
    type_sum(new.env()),
    type_sum(NULL)
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
