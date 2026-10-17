suppressPackageStartupMessages(library(stringdist))
if (packageDescription("stringdist")$Version != "0.9.17") stop("expected stringdist 0.9.17")
options(sd_num_thread = 1L)

column_major <- function(mat) {
  as.vector(mat)
}

numeric_part <- function(L) {
  c(column_major(L$location), column_major(L$distance))
}

one <- function() {
  texts <- c(
    "When I grow up, I want to be",
    "one of the harvesters of the sea",
    "I think before my days are gone",
    "I want to be a fisherman"
  )
  patterns <- c("fish", "gone", "to be")
  parts <- list(
    numeric_part(afind(texts, patterns, method = "running_cosine", q = 3)),
    numeric_part(afind("abcabc", "bc", method = "osa")),
    numeric_part(afind("aaaa", "aa", method = "osa")),
    numeric_part(afind("Mot\u00f6rhead", "tor", useBytes = TRUE, method = "osa")),
    numeric_part(afind("Mot\u00f6rhead", "tor", useBytes = FALSE, method = "osa")),
    numeric_part(afind(c(NA, "abc"), "bc", method = "osa")),
    numeric_part(afind("abcdef", c("bc", "de"), method = "osa")),
    numeric_part(afind("survey", "surgery", method = "jw", p = 0.1)),
    numeric_part(afind("ab", "ba", method = "hamming")),
    numeric_part(afind("abc", "cba", method = "cosine", q = 2)),
    numeric_part(afind(texts, patterns, method = "running_cosine", q = 3, value = FALSE))
  )
  unlist(parts, use.names = FALSE)
}

fmt <- function(v) {
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
