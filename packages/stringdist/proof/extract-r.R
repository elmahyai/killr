suppressPackageStartupMessages(library(stringdist))
if (packageDescription("stringdist")$Version != "0.9.17") stop("expected stringdist 0.9.17")
options(sd_num_thread = 1L)

column_major <- function(mat) {
  as.vector(mat)
}

one <- function() {
  texts <- c(
    "When I grow up, I want to be",
    "one of the harvesters of the sea",
    "I think before my days are gone",
    "I want to be a fisherman"
  )
  parts <- list(
    column_major(extract(texts, "harvested", maxDist = 3)),
    column_major(extract(texts, "fish", maxDist = 0.5)),
    column_major(extract(texts, "gone", maxDist = Inf)),
    column_major(extract("abcabc", "bc", maxDist = 0)),
    column_major(extract("abcabc", "bc", maxDist = 1)),
    column_major(extract(c(NA, "abc"), "bc", maxDist = 1)),
    column_major(extract("Mot\u00f6rhead", "tor", useBytes = TRUE, maxDist = 2, method = "osa")),
    column_major(extract("abcdef", "bcd", method = "lv", maxDist = 1)),
    column_major(extract("ab", "ba", method = "hamming", maxDist = 2)),
    column_major(extract("abc", "cba", method = "cosine", q = 2, maxDist = 1)),
    column_major(extract(texts, "to be", method = "running_cosine", q = 3, maxDist = 0.2))
  )
  unlist(parts, use.names = FALSE)
}

quote_json <- function(v) {
  if (is.na(v)) return("null")
  paste0('"', gsub('(["\\\\])', '\\\\\\1', v, perl = TRUE), '"')
}

fmt <- function(v) {
  if (is.character(v)) return(quote_json(v))
  if (is.nan(v)) return('"NaN"')
  if (is.na(v)) return("null")
  if (is.infinite(v)) return(if (v > 0) '"Inf"' else '"-Inf"')
  sprintf("%.17g", v)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(vapply(value, fmt, ""), collapse = ","),
  median(elapsed) * 1000
))
