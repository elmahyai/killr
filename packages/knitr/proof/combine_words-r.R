suppressPackageStartupMessages(library(knitr))
stopifnot(as.character(packageVersion("knitr")) == "1.52")
json_str <- function(s) {
  if (length(s) == 0 || is.na(s)) return("null")
  chars <- strsplit(enc2utf8(s), "", fixed = TRUE)[[1]]
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
one <- function() combine_words(c("a", "b", "c"), before = "`")
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_str(value), median(elapsed) * 1000))
