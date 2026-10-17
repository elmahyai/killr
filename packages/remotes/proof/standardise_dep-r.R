.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))

json_str <- function(s) {
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

json_val <- function(x) {
  if (length(x) == 0) return("[]")
  paste0("[", paste(vapply(x, json_str, ""), collapse = ","), "]")
}

one <- function() standardise_dep(c("Enhances", "Imports", "extra"))
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
