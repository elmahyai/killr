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
  stri_startswith_fixed(
    c(rep(c("a1", "ba", "éab"), 700), "", NA_character_, "Ébc"),
    c(rep(c("a", "b", "ab"), 700), "a", "a", "éb"),
    from = c(rep(c(1L, 1L, 2L), 700), 1L, 1L, 1L),
    case_insensitive = TRUE
  )
}

out <- "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_startswith_fixed-r.txt"
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
sentence <- paste0('stri_startswith_fixed(c("a1", "a2", "b3", "a4", "c5"), "a") returns ', paste(stri_startswith_fixed(c("a1", "a2", "b3", "a4", "c5"), "a"), collapse = ", "), '.')
writeLines(sentence, out)

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"value\":%s,\"median_ms\":%.17g}\n", encode(value), median(elapsed) * 1000))
