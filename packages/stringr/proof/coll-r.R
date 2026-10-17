.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
stopifnot(packageVersion("stringr") == "1.6.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
writeLines(
  "coll(\"i\", ignore_case = TRUE, locale = \"tr\") stores locale tr and strength 2.",
  file.path(out_dir, "coll-r.txt")
)

json_escape <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s <- gsub("\r", "\\r", s, fixed = TRUE)
  paste0("\"", s, "\"")
}
json_atom <- function(x) {
  if (length(x) != 1) stop("option length")
  if (is.na(x) && !is.nan(x)) return("null")
  if (is.logical(x)) return(if (isTRUE(x)) "true" else "false")
  if (is.numeric(x)) return(sprintf("%.17g", x))
  if (is.character(x)) return(json_escape(x))
  stop("unexpected option value")
}
encode_opts <- function(opts) {
  if (is.null(opts) || length(opts) == 0) return("[]")
  parts <- character(length(opts))
  nms <- names(opts)
  for (i in seq_along(opts)) {
    parts[[i]] <- paste0("[", json_escape(nms[[i]]), ",", json_atom(opts[[i]]), "]")
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
encode_pattern <- function(x) {
  chars <- as.character(x)
  if (length(chars) == 0) return("[]")
  parts <- character(length(chars))
  for (i in seq_along(chars)) {
    parts[[i]] <- if (is.na(chars[[i]])) "null" else json_escape(chars[[i]])
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
kind_of <- function(x) {
  switch(class(x)[[1]],
    stringr_fixed = "fixed",
    stringr_coll = "coll",
    stringr_regex = "regex",
    stringr_boundary = "bound",
    class(x)[[1]]
  )
}
encode_one <- function(x) {
  paste0(
    "{\"kind\":", json_escape(kind_of(x)),
    ",\"pattern\":", encode_pattern(x),
    ",\"options\":", encode_opts(attr(x, "options")), "}"
  )
}
encode_value <- function(items) {
  paste0("[", paste(vapply(items, encode_one, ""), collapse = ","), "]")
}

one <- function() {
  list(
    coll("a"),
    coll("a", TRUE),
    coll("a", TRUE, strength = 1),
    coll("i", TRUE, locale = "tr"),
    coll("a", numeric = TRUE),
    coll("a", strength = NULL),
    coll("a", strength = NA)
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
