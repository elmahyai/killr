.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(stringi))
stopifnot(packageVersion("stringi") == "1.8.9")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
writeLines(
  "stri_opts_collator(numeric = TRUE) returns numeric TRUE.",
  file.path(out_dir, "stri_opts_collator-r.txt")
)

json_escape <- function(s) {
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  paste0("\"", s, "\"")
}
json_atom <- function(x) {
  if (is.logical(x) && length(x) == 1 && !is.na(x)) return(if (isTRUE(x)) "true" else "false")
  if (is.numeric(x) && length(x) == 1 && !is.na(x)) return(sprintf("%.17g", x))
  if (is.character(x) && length(x) == 1 && !is.na(x)) return(json_escape(x))
  stop("unexpected option value")
}
encode_opts <- function(opts) {
  if (length(opts) == 0) return("[]")
  parts <- character(length(opts))
  nms <- names(opts)
  for (i in seq_along(opts)) {
    parts[[i]] <- paste0("[", json_escape(nms[[i]]), ",", json_atom(opts[[i]]), "]")
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
encode_value <- function(items) {
  paste0("[", paste(vapply(items, encode_opts, ""), collapse = ","), "]")
}

one <- function() {
  list(
    stri_opts_collator(),
    stri_opts_collator(locale = "en", strength = 1L, numeric = TRUE, normalisation = TRUE)
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', encode_value(value), median(elapsed) * 1000))
