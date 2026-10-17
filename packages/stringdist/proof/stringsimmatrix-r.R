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
short <- words[1:8]

column_major <- function(mat) {
  if (length(mat) == 0L) return(numeric(0))
  as.vector(mat)
}

one <- function() {
  parts <- list(
    column_major(stringsimmatrix(short, short[3:5], method = "osa")),
    column_major(stringsimmatrix(short, short[3:5], method = "dl", weight = c(0.5, 0.8, 0.3, 0.4))),
    column_major(stringsimmatrix(short, short[3:5], method = "jw", p = 0.1)),
    column_major(stringsimmatrix(short, short[3:5], method = "cosine", q = 2)),
    column_major(stringsimmatrix(c("ab", "abc"), c("ba", "abc"), method = "hamming")),
    column_major(stringsimmatrix(c("a", NA, "b"), c("aa", "bb", "b"))),
    column_major(stringsimmatrix(character(0), c("a", "b"))),
    column_major(stringsimmatrix(short, method = "osa")),
    column_major(stringsimmatrix(short[1:4], method = "lcs")),
    column_major(stringsimmatrix(c("Euler", "Ellery", "Gauss"), method = "soundex")),
    column_major(stringsimmatrix(c("Mot\u00f6rhead", "Motorhead"), method = "dl", useBytes = TRUE)),
    column_major(
      stringsimmatrix(
        c("ca", "abc"),
        c("abc", "ca"),
        weight = c(0.5, 1, 1, 1)
      )
    )
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
