.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))

json_str <- function(s) {
  if (is.na(s)) return("null")
  bytes <- as.integer(charToRaw(enc2utf8(s)))
  parts <- character(length(bytes))
  for (i in seq_along(bytes)) {
    b <- bytes[[i]]
    parts[[i]] <- if (b == 34) paste0("\\", '"')
      else if (b == 92) paste0("\\", "\\")
      else if (b == 10) paste0("\\", "n")
      else if (b == 13) paste0("\\", "r")
      else if (b == 9) paste0("\\", "t")
      else if (b < 32 || b == 127) sprintf("\\u%04x", b)
      else intToUtf8(b)
  }
  paste0('"', paste(parts, collapse = ""), '"')
}

json_obj <- function(x) {
  parts <- vapply(names(x), function(nm) {
    paste0(json_str(nm), ":", json_str(x[[nm]]))
  }, "")
  paste0("{", paste(parts, collapse = ","), "}")
}

one <- function() {
  parse_github_url("https://github.com/r-lib/remotes/releases/tag/1.0.0")
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
  json_obj(value),
  median(elapsed) * 1000
))
