suppressPackageStartupMessages(library(stringi))

esc <- function(x) {
  x <- enc2utf8(x)
  x <- gsub("\\", "\\\\", x, fixed = TRUE)
  x <- gsub("\"", "\\\"", x, fixed = TRUE)
  x <- gsub("\r", "\\r", x, fixed = TRUE)
  x <- gsub("\n", "\\n", x, fixed = TRUE)
  x <- gsub("\t", "\\t", x, fixed = TRUE)
  paste0("\"", x, "\"")
}

atom <- function(x) {
  if (is.character(x)) {
    if (is.na(x)) "null" else esc(x)
  } else if (is.logical(x)) {
    if (is.na(x)) "null" else if (isTRUE(x)) "true" else "false"
  } else if (is.numeric(x)) {
    if (is.na(x)) "null" else as.character(x)
  } else {
    stop("atom")
  }
}

vec <- function(x) {
  if (length(x) == 0) return("[]")
  paste0("[", paste(vapply(seq_along(x), function(i) atom(x[[i]]), ""), collapse = ","), "]")
}

mat <- function(m) {
  if (is.null(dim(m)) || nrow(m) == 0) return("[]")
  rows <- lapply(seq_len(nrow(m)), function(i) vec(m[i, ]))
  paste0("[", paste(rows, collapse = ","), "]")
}

lst <- function(x, each) {
  if (length(x) == 0) return("[]")
  paste0("[", paste(vapply(seq_along(x), function(i) each(x[[i]]), ""), collapse = ","), "]")
}

encode <- function(x) {
  vec(x)
}

one <- function() {
  stri_replace_all_fixed(
    c(rep("aAaA", 1200), "aaa", "", NA_character_, "abc"),
    c(rep("a", 1200), "aa", "a", "a", "z"),
    c(rep("X", 1200), "b", "Z", "Z", "Q"),
    vectorize_all = TRUE,
    opts_fixed = stri_opts_fixed(case_insensitive = TRUE, overlap = TRUE)
  )
}

out <- "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_replace_all_fixed-r.txt"
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
sentence <- paste0('stri_replace_all_fixed("aAaA", "a", "X", case_insensitive=TRUE) returns ', stri_replace_all_fixed("aAaA", "a", "X", case_insensitive = TRUE), '.')
writeLines(sentence, out)

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"value\":%s,\"median_ms\":%.17g}\n", encode(value), median(elapsed) * 1000))
