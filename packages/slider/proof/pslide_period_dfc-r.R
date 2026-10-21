.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(slider))
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
  if (length(x) == 1 && is.character(x)) return(json_str(x))
  x <- as.character(x)
  if (length(x) == 1) return(json_str(x[[1]]))
  paste0("[", paste(vapply(x, json_str, ""), collapse = ","), "]")
}
x <- c(1, 5, 3, 2, 6, 10)
y <- c(2, 4, 1, 3, 5, 7)
i <- c(0, 1, 3, 4, 6, 8)
d <- as.Date("2020-01-01") + i
frame_text <- function(value) {
  cell <- function(v) {
    if (is.numeric(v)) return(ifelse(is.na(v), "NA", sprintf("%.17e", as.numeric(v))))
    if (is.logical(v)) return(ifelse(is.na(v), "NA", ifelse(v, "TRUE", "FALSE")))
    ifelse(is.na(v), "NA", as.character(v))
  }
  rows <- vapply(seq_len(nrow(value)), function(row) {
    paste(vapply(seq_along(value), function(col) cell(value[[col]][[row]]), ""), collapse = ":")
  }, "")
  paste0(paste(names(value), collapse = ","), "::", paste(rows, collapse = ";"))
}

one <- function() {
  frame_text(pslide_period_dfc(list(x, y), d, "day", function(a, b) data.frame(s = a[[1]] + b[[1]]), .before = 1))
}
value <- one()
elapsed <- numeric(20)
for (step_i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[step_i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
