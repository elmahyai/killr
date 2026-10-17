.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(pillar))

json_str <- function(s) {
  chars <- strsplit(s, "", fixed = TRUE)[[1]]
  if (!length(chars)) return('""')
  out <- vapply(chars, function(ch) {
    code <- utf8ToInt(ch)
    if (ch == "\\") return("\\\\")
    if (ch == "\"") return("\\\"")
    if (code < 32L) return(sprintf("\\u%04x", code))
    ch
  }, "")
  paste0('"', paste(out, collapse = ""), '"')
}

encode_data <- function(x) {
  if (!length(x)) return("[]")
  parts <- vapply(seq_along(x), function(i) {
    if (is.na(x[[i]])) "null" else json_str(x[[i]])
  }, "")
  paste0("[", paste(parts, collapse = ","), "]")
}

encode <- function(items) {
  parts <- vapply(items, function(item) {
    paste0(
      '{"data":', encode_data(item$data),
      ',"type":', json_str(item$type), "}"
    )
  }, "")
  paste0("[", paste(parts, collapse = ","), "]")
}

one <- function() {
  items <- list(
    set_char_opts(c("a", "bb"), min_chars = 5, shorten = "mid"),
    set_char_opts(c("a", NA)),
    set_char_opts("hello", min_chars = 3, shorten = "abbreviate"),
    set_char_opts("ab", shorten = "back"),
    set_char_opts(c("ab", "cd"), min_chars = 2, shorten = "front")
  )
  lapply(items, function(x) {
    list(data = x, type = format(attr(x, "pillar", exact = TRUE)))
  })
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":%s,"median_ms":%.17g}\n',
  encode(value),
  median(elapsed) * 1000
))
