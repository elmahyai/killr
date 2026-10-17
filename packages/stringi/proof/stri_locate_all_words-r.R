.libPaths(c(
  path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"),
  path.expand("~/R/library"),
  .libPaths()
))
suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")

esc <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  s <- gsub("\r", "\\r", s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s <- gsub("\t", "\\t", s, fixed = TRUE)
  s
}
json_scalar <- function(x) {
  if (is.character(x)) {
    if (is.na(x)) return("null")
    return(paste0("\"", esc(x), "\""))
  }
  if (is.logical(x)) {
    if (is.na(x)) return("null")
    return(if (isTRUE(x)) "true" else "false")
  }
  if (is.numeric(x)) {
    if (is.na(x)) return("null")
    return(sprintf("%.17g", as.numeric(x)))
  }
  "null"
}
json_val <- function(x) {
  if (is.null(x)) return("null")
  if (is.matrix(x)) {
    if (nrow(x) == 0) return("[]")
    rows <- character(nrow(x))
    for (i in seq_len(nrow(x))) {
      cells <- character(ncol(x))
      for (j in seq_len(ncol(x))) cells[[j]] <- json_scalar(x[i, j])
      rows[[i]] <- paste0("[", paste(cells, collapse = ","), "]")
    }
    return(paste0("[", paste(rows, collapse = ","), "]"))
  }
  if (is.list(x)) {
    if (length(x) == 0) return("[]")
    return(paste0("[", paste(vapply(x, json_val, ""), collapse = ","), "]"))
  }
  if (length(x) == 0) return("[]")
  paste0("[", paste(vapply(seq_along(x), function(i) json_scalar(x[[i]]), ""), collapse = ","), "]")
}

writeLines(
  "stri_locate_all_words(\"ab cd\") starts at 1, 4.",
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_locate_all_words-r.txt"
)

one <- function() {
  en <- rep(c("a\U0001F600bc def", "ab cd", "...", "", NA), 25)
  list(
    stri_locate_all_words(en),
    stri_locate_all_words(en, get_length = TRUE),
    stri_locate_all_words(rep("\u79c1\u306f\u65e5\u672c\u8a9e\u3092\u8a71\u3057\u307e\u3059", 15), locale = "ja", get_length = TRUE)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0(
  '{"value":', json_val(value),
  ',"median_ms":', sprintf("%.17g", median(elapsed) * 1000),
  '}\n'
))
