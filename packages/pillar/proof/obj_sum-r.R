.libPaths(c(path.expand("~/R/library"), .libPaths()))
options(cli.unicode = TRUE)
suppressPackageStartupMessages(library(pillar))

json_str <- function(s) {
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  paste0('"', s, '"')
}

json_chr <- function(xs) {
  paste0("[", paste(vapply(xs, json_str, ""), collapse = ","), "]")
}

json_opt <- function(xs) {
  parts <- character(length(xs))
  for (i in seq_along(xs)) {
    s <- xs[[i]]
    parts[[i]] <- if (is.na(s)) "null" else json_str(s)
  }
  paste0("[", paste(parts, collapse = ","), "]")
}

one <- function() {
  xs <- list(
    1:10,
    matrix(1:10),
    data.frame(a = 1),
    Sys.Date(),
    Sys.time(),
    mean,
    list(1, 2),
    NULL,
    new.env(),
    Titanic
  )
  values <- character(length(xs))
  shorts <- rep(NA_character_, length(xs))
  for (i in seq_along(xs)) {
    s <- obj_sum(xs[[i]])
    values[[i]] <- as.character(s)
    sh <- attr(s, "short", exact = TRUE)
    if (!is.null(sh)) shorts[[i]] <- sh
  }
  list(value = values, short = shorts)
}

packed <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":%s,"short":%s,"median_ms":%.17g}\n',
  json_chr(packed$value),
  json_opt(packed$short),
  median(elapsed) * 1000
))
