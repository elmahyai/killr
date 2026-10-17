.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
stopifnot(packageVersion("stringr") == "1.6.0")
stopifnot(packageVersion("stringi") == "1.8.9")

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

encode <- function(x) {
  if (is.null(x)) return("null")
  if (is.list(x)) {
    if (length(x) == 0) return("[]")
    parts <- vapply(x, encode, "")
    return(paste0("[", paste(parts, collapse = ","), "]"))
  }
  if (length(x) == 0) return("[]")
  paste0("[", paste(vapply(seq_along(x), function(i) atom(x[[i]]), ""), collapse = ","), "]")
}

fruit <- c("apple", "banana", "pear", "pineapple")
stopifnot(identical(str_like(fruit, "app%"), c(TRUE, FALSE, FALSE, FALSE)))
sentence <- 'str_like(c("apple", "banana", "pear", "pineapple"), "app%") returns TRUE, FALSE, FALSE, FALSE.'
out_path <- "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_like-r.txt"
dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)
writeLines(sentence, out_path)

one <- function() {
  base <- c("apple", "banana", "pear", "pineapple", NA_character_, "", "a\U0001F600b", "X.", "stra\u00dfe", "a\nb")
  texts <- rep(base, 20)
  list(
    str_like(texts, "a%"),
    str_like(texts, "%a%"),
    str_like(c("ab%", "abX", "a_b", "100", "NA", NA_character_), c("ab\\%", "ab_", "a\\_b", "100%", NA_character_, "%"))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"value\":%s,\"median_ms\":%.17g}\n", encode(value), median(elapsed) * 1000))
