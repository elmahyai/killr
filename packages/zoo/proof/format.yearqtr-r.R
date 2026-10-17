.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(zoo))
stopifnot(packageVersion("zoo") == "1.9-1")
json_chr <- function(x) {
  if (length(x) == 0) return("[]")
  parts <- character(length(x))
  for (i in seq_along(x)) {
    if (is.na(x[[i]])) {
      parts[[i]] <- "null"
    } else {
      s <- gsub("\\\\", "\\\\\\\\", x[[i]], fixed = TRUE)
      s <- gsub("\"", "\\\"", s, fixed = TRUE)
      parts[[i]] <- paste0("\"", s, "\"")
    }
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
one <- function() format(as.yearqtr(c(2000, 2001.25, 99.75, -1.5, NA)), "%Y Q%q | %y | %C")
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_chr(value), median(elapsed) * 1000))
