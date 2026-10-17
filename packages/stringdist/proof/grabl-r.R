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
  c(
    grabl(texts, "fish", maxDist = 0.5),
    grabl(texts, "gone", maxDist = Inf),
    grabl(texts, "grew", maxDist = 1),
    grabl("abcabc", "bc", maxDist = 0),
    grabl("abcabc", "bc", maxDist = 1),
    grabl(c(NA, "abc"), "bc", maxDist = 1),
    grabl("Mot\u00f6rhead", "tor", useBytes = TRUE, maxDist = 2, method = "osa"),
    grabl("abcdef", "bcd", method = "lv", maxDist = 1),
    grabl("ab", "ba", method = "hamming", maxDist = 2),
    grabl("abc", "cba", method = "cosine", q = 2, maxDist = 1),
    grabl("foo", ""),
    grabl("foo", NA),
    grabl(NA, "foo"),
    grabl("", "foo", maxDist = 3)
  )
}

# Flags are numeric so max_abs_diff applies: TRUE = 1, FALSE = 0, NA = null.
fmt_flag <- function(v) {
  if (is.na(v)) return("null")
  if (v) "1" else "0"
}

result <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(vapply(result, fmt_flag, ""), collapse = ","),
  median(elapsed) * 1000
))
