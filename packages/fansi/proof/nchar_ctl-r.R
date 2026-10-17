.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(fansi))
json_str <- function(s) {
  if (length(s) == 0 || is.na(s)) return("null")
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
  if (is.logical(x)) {
    parts <- ifelse(is.na(x), "null", ifelse(x, "true", "false"))
    if (length(x) == 1) return(parts[[1]])
    return(paste0("[", paste(parts, collapse=","), "]"))
  }
  if (is.numeric(x) && length(x) == 1 && !is.na(x)) return(sprintf("%.17g", x))
  x <- as.character(x)
  if (length(x) == 1) return(json_str(x[[1]]))
  paste0("[", paste(vapply(x, json_str, ""), collapse = ","), "]")
}

one <- function() {
  nchar_ctl(c("\033[31m123\a\r", paste0("\033[31m", "\u4e00\u4e01\u4e03", "\a\r"), paste0("hello", "\u0300\u035c", " world"), paste0("A", "\u030a"), "\U0001F468\u200D\U0001F469\u200D\U0001F467", "\U0001F1FA\U0001F1F8", "\t\n\r"), type="width", warn=FALSE)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
