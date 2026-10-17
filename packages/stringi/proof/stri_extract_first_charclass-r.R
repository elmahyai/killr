.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")

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
  } else stop("atom")
}
vec <- function(x) {
  if (length(x) == 0) return("[]")
  paste0("[", paste(vapply(seq_along(x), function(i) atom(x[[i]]), ""), collapse = ","), "]")
}
encode <- function(x) {
  if (is.list(x)) {
    if (length(x) == 0) return("[]")
    paste0("[", paste(vapply(x, encode, ""), collapse = ","), "]")
  } else if (is.matrix(x)) {
    if (nrow(x) == 0) return("[]")
    rows <- lapply(seq_len(nrow(x)), function(i) vec(x[i, ]))
    paste0("[", paste(rows, collapse = ","), "]")
  } else vec(x)
}

tod <- "\U000105C0"
emoji <- "\U0001F600"
text <- rep(c(
  "Abc def\t12",
  "  éÉ  ",
  paste0(tod, " 9"),
  paste0("a", emoji, "b c"),
  " \u00A0\t",
  "",
  NA_character_
), 150)
pat <- c("\\p{L}", "\\p{N}", "\\p{WhiteSpace}", "\\p{Z}", "\\p{Lo}", "[:digit:]", "\\p{Emoji}")

x <- stri_extract_first_charclass("AaBb", "\\p{Ll}")
sentence <- paste0('stri_extract_first_charclass("AaBb", "\\p{Ll}") returns ', x, '.')

out <- "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_extract_first_charclass-r.txt"
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
writeLines(sentence, out)

one <- function() {
  stri_extract_first_charclass(text, pat)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"value\":%s,\"median_ms\":%.17g}\n", encode(value), median(elapsed) * 1000))
