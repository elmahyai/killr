.libPaths(c(path.expand("~/R/library"), .libPaths()))
options(cli.num_colors = 8)
suppressPackageStartupMessages(library(pillar))
options(pillar.subtle = TRUE)

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

encode <- function(value) {
  if (length(value) == 1) return(json_str(value))
  paste0("[", paste(vapply(value, json_str, ""), collapse = ","), "]")
}

one <- function() format_type_sum("dbl", NULL)
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
