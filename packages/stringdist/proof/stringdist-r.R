suppressPackageStartupMessages(library(stringdist))
if (packageDescription("stringdist")$Version != "0.9.17") stop("expected stringdist 0.9.17")
options(sd_num_thread = 1L)

words <- c(
  "ca", "abc", "MARTHA", "MATHRA", "survey", "surgery",
  "leia", "leela", "crate", "trace", "dixon", "dicksonx",
  "john doe", "jane doe", "sock", "sck", "Euler", "Ellery",
  "Mot\u00f6rhead", "Motorhead", "abcabc", "aaa", "hello", "HeLl0",
  "DHCXXXXX", "HCDXXXXX", "RICK WARREN", "WARREN BUFFET",
  "", "a"
)

one <- function() {
  extra <- numeric(0)
  for (i in seq_len(length(words) - 1L)) {
    extra <- c(
      extra,
      stringdist(words[[i]], words[[i + 1L]], method = "osa"),
      stringdist(words[[i]], words[[i + 1L]], method = "dl", weight = c(0.5, 0.8, 0.3, 0.4)),
      stringdist(words[[i]], words[[i + 1L]], method = "jw", p = 0.1),
      stringdist(words[[i]], words[[i + 1L]], method = "cosine", q = 2)
    )
  }
  c(
    stringdist("ca", "abc"),
    stringdist("ca", "abc", method = "dl"),
    stringdist("ABC", "abc"),
    stringdist(tolower("ABC"), "abc"),
    stringdist(c("a", "b", "c", "d"), c("a", "c")),
    stringdist("ab", "ba", weight = c(1, 1, 1, 0.5)),
    stringdist("ca", "abc", weight = c(0.5, 1, 1, 1)),
    stringdist("abc", "ca", weight = c(0.5, 1, 1, 1)),
    stringdist("hello", "HeLl0", method = "h"),
    stringdist("ab", "abc", method = "hamming"),
    stringdist("ab", "ba", method = "lcs"),
    stringdist("survey", "surgery", method = "lcs"),
    stringdist("abc", "cba", method = "qgram", q = 1),
    stringdist("abc", "cba", method = "qgram", q = 2),
    stringdist("abcd", "abxd", method = "qgram", q = 2.9),
    stringdist("aaa", "abc", method = "cosine", q = 1),
    stringdist("abc", "abcabc", method = "cosine", q = 1),
    stringdist("ab", "ab", method = "cosine"),
    stringdist("", "a", method = "cosine"),
    stringdist("aaa", "abc", method = "jaccard", q = 1),
    stringdist("", "", method = "jaccard"),
    stringdist("a", "b", method = "jaccard", q = 2),
    stringdist("MARTHA", "MATHRA", method = "jw"),
    stringdist("MARTHA", "MATHRA", method = "jw", p = 0.1),
    stringdist("crate", "trace", method = "jw", weight = c(0.5, 1, 1)),
    stringdist("axiou", "aaeeiioouu", method = "jw"),
    stringdist("john doe", "jane doe", method = "jw", p = 0.1, bt = 0.8),
    stringdist("Euler", "Gauss", method = "soundex"),
    stringdist("Euler", "Ellery", method = "soundex"),
    stringdist("sock", "sck", method = "soundex"),
    stringdist("Mot\u00f6rhead", "Motorhead", method = "dl"),
    stringdist("Mot\u00f6rhead", "Motorhead", method = "dl", useBytes = TRUE),
    stringdist("Mot\u00f6rhead", "Motorhead", method = "hamming", useBytes = TRUE),
    stringdist("Mot\u00f6rhead", "Motorhead", method = "jw", useBytes = TRUE),
    stringdist("leia", "leela", method = "lv", weight = c(0.1, 1, 1)),
    stringdist("leia", "leela", method = "dl", weight = c(1, 0.1, 1, 1)),
    stringdist(c("a", NA, "b"), c("aa", "bb", "b")),
    stringdist("", ""),
    stringdist("", "a"),
    extra
  )
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
