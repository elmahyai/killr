.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
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

text <- rep(c("ab", "12", "", NA_character_, "c9"), 400)
x <- `stri_subset_charclass<-`(c("ab", "12", "c"), "\\p{L}", value = "L")
sentence <- paste0('`stri_subset_charclass<-`(c("ab", "12", "c"), "\\p{L}", value="L") returns ', paste(x, collapse = ", "), '.')
out <- "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_subset_charclass<--r.txt"
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
writeLines(sentence, out)

one <- function() {
  `stri_subset_charclass<-`(text, "\\p{N}", value = "D")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"value\":%s,\"median_ms\":%.17g}\n", vec(value), median(elapsed) * 1000))
