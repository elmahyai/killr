suppressPackageStartupMessages(library(stringdist))
if (packageDescription("stringdist")$Version != "0.9.17") stop("expected stringdist 0.9.17")
options(sd_num_thread = 1L)

one <- function() {
  texts <- c(
    "When I grow up, I want to be",
    "one of the harvesters of the sea",
    "I think before my days are gone",
    "I want to be a fisherman"
  )
  idx <- as.numeric(c(
    grab(texts, "fish", maxDist = 0.5),
    grab(texts, "gone", maxDist = Inf),
    grab(texts, "grew", maxDist = 1),
    grab("abcabc", "bc", maxDist = 0),
    grab("abcabc", "bc", maxDist = 1),
    grab(c(NA, "abc"), "bc", maxDist = 1),
    grab("Mot\u00f6rhead", "tor", useBytes = TRUE, maxDist = 2, method = "osa"),
    grab("abcdef", "bcd", method = "lv", maxDist = 1),
    grab("ab", "ba", method = "hamming", maxDist = 2),
    grab("abc", "cba", method = "cosine", q = 2, maxDist = 1)
  ))
  strings <- c(
    grab(texts, "fish", maxDist = 0.5, value = TRUE),
    grab(texts, "to be", method = "running_cosine", q = 3, maxDist = 0.2, value = TRUE)
  )
  list(idx = idx, strings = strings)
}

quote_json <- function(v) {
  if (is.na(v)) return("null")
  paste0('"', gsub('(["\\\\])', '\\\\\\1', v, perl = TRUE), '"')
}

fmt_num <- function(v) {
  if (is.nan(v)) return('"NaN"')
  if (is.na(v)) return("null")
  if (is.infinite(v)) return(if (v > 0) '"Inf"' else '"-Inf"')
  sprintf("%.17g", v)
}

result <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":[%s],"strings":[%s],"median_ms":%.17g}\n',
  paste(vapply(result$idx, fmt_num, ""), collapse = ","),
  paste(vapply(result$strings, quote_json, ""), collapse = ","),
  median(elapsed) * 1000
))
