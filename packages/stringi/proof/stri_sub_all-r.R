.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- sub("^--file=", "", file_arg[[1]])
out <- file.path(dirname(normalizePath(script)), "..", "docs", "output", "stri_sub_all-r.txt")
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
quote_one <- function(z) if (is.na(z)) "NA" else sprintf("\"%s\"", z)
join_words <- function(x) {
  parts <- vapply(x, quote_one, "")
  n <- length(parts)
  if (n <= 1) return(paste(parts, collapse = ""))
  if (n == 2) return(paste(parts, collapse = " and "))
  paste0(paste(parts[-n], collapse = ", "), ", and ", parts[n])
}
esc <- function(s) {
  if (is.na(s)) return("null")
  s <- gsub("\\\\", "\\\\\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\\\"", s, fixed = TRUE)
  s <- gsub("\n", "\\\\n", s, fixed = TRUE)
  s <- gsub("\r", "\\\\r", s, fixed = TRUE)
  s <- gsub("\t", "\\\\t", s, fixed = TRUE)
  paste0("\"", s, "\"")
}
vec <- function(x) {
  if (length(x) == 0) return("[]")
  paste0("[", paste(vapply(seq_along(x), function(i) esc(x[[i]]), ""), collapse = ","), "]")
}
json_val <- function(x) {
  if (is.list(x)) {
    if (length(x) == 0) return("[]")
    return(paste0("[", paste(vapply(x, vec, ""), collapse = ","), "]"))
  }
  vec(x)
}

res <- stri_sub_all("a b c", c(1, 3, 5), c(1, 3, 5))
writeLines(paste0('stri_sub_all("a b c", c(1, 3, 5), c(1, 3, 5)) returns ', join_words(res[[1]]), "."), out)


one <- function() {
  stri_sub_all(
    rep(c("a b c", "", NA), 80),
    list(c(1, 3, 5), c(1, 10), 1),
    list(c(1, 3, 5), c(1, 12), 1)
  )
}


value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
