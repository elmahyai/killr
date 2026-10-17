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
      stringsim(words[[i]], words[[i + 1L]], method = "osa"),
      stringsim(words[[i]], words[[i + 1L]], method = "dl", weight = c(0.5, 0.8, 0.3, 0.4)),
      stringsim(words[[i]], words[[i + 1L]], method = "jw", p = 0.1),
      stringsim(words[[i]], words[[i + 1L]], method = "cosine", q = 2)
    )
  }
  c(
    stringsim("ca", "abc"),
    stringsim("ca", "abc", method = "dl"),
    stringsim("ABC", "abc"),
    stringsim(tolower("ABC"), "abc"),
    stringsim(c("a", "b", "c", "d"), c("a", "c")),
    stringsim("ab", "ba", weight = c(1, 1, 1, 0.5)),
    stringsim("ca", "abc", weight = c(0.5, 1, 1, 1)),
    stringsim("abc", "ca", weight = c(0.5, 1, 1, 1)),
    stringsim("hello", "HeLl0", method = "h"),
    stringsim("ab", "abc", method = "hamming"),
    stringsim("ab", "ba", method = "lcs"),
    stringsim("survey", "surgery", method = "lcs"),
    stringsim("abc", "cba", method = "qgram", q = 1),
    stringsim("abc", "cba", method = "qgram", q = 2),
    stringsim("abcd", "abxd", method = "qgram", q = 2.9),
    stringsim("aaa", "abc", method = "cosine", q = 1),
    stringsim("abc", "abcabc", method = "cosine", q = 1),
    stringsim("ab", "ab", method = "cosine"),
    stringsim("", "a", method = "cosine"),
    stringsim("aaa", "abc", method = "jaccard", q = 1),
    stringsim("", "", method = "jaccard"),
    stringsim("a", "b", method = "jaccard", q = 2),
    stringsim("MARTHA", "MATHRA", method = "jw"),
    stringsim("MARTHA", "MATHRA", method = "jw", p = 0.1),
    stringsim("crate", "trace", method = "jw", weight = c(0.5, 1, 1)),
    stringsim("axiou", "aaeeiioouu", method = "jw"),
    stringsim("john doe", "jane doe", method = "jw", p = 0.1, bt = 0.8),
    stringsim("Euler", "Gauss", method = "soundex"),
    stringsim("Euler", "Ellery", method = "soundex"),
    stringsim("sock", "sck", method = "soundex"),
    stringsim("Mot\u00f6rhead", "Motorhead", method = "dl"),
    stringsim("Mot\u00f6rhead", "Motorhead", method = "dl", useBytes = TRUE),
    stringsim("Mot\u00f6rhead", "Motorhead", method = "hamming", useBytes = TRUE),
    stringsim("Mot\u00f6rhead", "Motorhead", method = "jw", useBytes = TRUE),
    stringsim("leia", "leela", method = "lv", weight = c(0.1, 1, 1)),
    stringsim("leia", "leela", method = "dl", weight = c(1, 0.1, 1, 1)),
    stringsim(c("a", NA, "b"), c("aa", "bb", "b")),
    stringsim("", ""),
    stringsim("", "a"),
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
