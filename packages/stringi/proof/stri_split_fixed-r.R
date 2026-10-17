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
  lst(x, vec)
}

one <- function() {
  stri_split_fixed(
    c(rep("a_b_c__d", 600), "", NA_character_),
    "_",
    n = c(rep(c(-1L, 2L, 4L), 200), -1L, -1L),
    omit_empty = FALSE,
    tokens_only = TRUE,
    simplify = FALSE
  )
}

out <- "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_split_fixed-r.txt"
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
sentence <- paste0('stri_split_fixed("a_b_c_d", "_") returns ', paste(stri_split_fixed("a_b_c_d", "_")[[1]], collapse = ", "), '.')
writeLines(sentence, out)

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"value\":%s,\"median_ms\":%.17g}\n", encode(value), median(elapsed) * 1000))
