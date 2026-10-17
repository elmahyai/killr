
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(jsonlite))
json_str <- function(s) {
  if (length(s) == 0 || is.na(s)) return("null")
  chars <- strsplit(enc2utf8(s), "")[[1]]
  parts <- character(length(chars))
  for (i in seq_along(chars)) {
    cp <- utf8ToInt(chars[[i]])
    parts[[i]] <- if (cp == 34) paste0("\\", '"')
      else if (cp == 92) paste0("\\", "\\")
      else if (cp == 10) paste0("\\", "n")
      else if (cp == 13) paste0("\\", "r")
      else if (cp == 9) paste0("\\", "t")
      else if (cp < 32 || cp == 127) sprintf("\\u%04x", cp)
      else chars[[i]]
  }
  paste0('"', paste(parts, collapse = ""), '"')
}
json_val <- function(x) {
  if (is.null(x)) return("null")
  if (is.logical(x)) {
    parts <- ifelse(is.na(x), "null", ifelse(x, "true", "false"))
    if (length(parts) == 1) return(parts[[1]])
    return(paste0("[", paste(parts, collapse = ","), "]"))
  }
  if (is.numeric(x)) {
    parts <- ifelse(is.na(x), "null", sprintf("%.17g", x))
    if (length(parts) == 1) return(parts[[1]])
    return(paste0("[", paste(parts, collapse = ","), "]"))
  }
  x <- as.character(x)
  if (length(x) == 1) return(json_str(x[[1]]))
  paste0("[", paste(vapply(x, json_str, ""), collapse = ","), "]")
}
one <- function() toJSON(list(foo = unbox(123)))
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
