.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
options(cli.num_colors = 1)
suppressPackageStartupMessages(library(stringr))
if (as.character(packageVersion("stringr")) != "1.6.0") stop("expected stringr 1.6.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
writeLines(
  capture.output(str_view_all(c("abc", "def", "fghi"), "e")),
  file.path(out_dir, "str_view_all-r.txt")
)

spans_of <- function(text) {
  if (is.na(text) || !nzchar(text)) return(list())
  chars <- strsplit(text, "", fixed = TRUE)[[1]]
  spans <- list()
  original <- 0L
  i <- 1L
  n <- length(chars)
  while (i <= n) {
    if (identical(chars[[i]], "<")) {
      start <- original + 1L
      i <- i + 1L
      buf_n <- 0L
      while (i <= n && !identical(chars[[i]], ">")) {
        buf_n <- buf_n + 1L
        i <- i + 1L
      }
      if (i <= n && identical(chars[[i]], ">")) i <- i + 1L
      if (buf_n == 0L) spans[[length(spans) + 1L]] <- c(start, start - 1L)
      else spans[[length(spans) + 1L]] <- c(start, start + buf_n - 1L)
      original <- original + buf_n
    } else {
      original <- original + 1L
      i <- i + 1L
    }
  }
  spans
}

view_record <- function(x) {
  text <- character(length(x))
  spans <- vector("list", length(x))
  for (i in seq_along(x)) {
    if (is.na(x[[i]])) {
      text[[i]] <- NA_character_
      spans[[i]] <- list()
    } else {
      text[[i]] <- cli::ansi_strip(x[[i]])
      spans[[i]] <- spans_of(text[[i]])
    }
  }
  list(ids = as.integer(attr(x, "id")), text = text, spans = spans)
}

one <- function() {
  view_record(str_view_all(c("abc", "def", "fghi", NA), "e"))
}

value <- suppressWarnings(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  suppressWarnings(one())
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":%s,"median_ms":%.17g}\n',
  jsonlite::toJSON(value, auto_unbox = FALSE, digits = 17, na = "null"),
  median(elapsed) * 1000
))
