suppressPackageStartupMessages(library(stringdist))
if (packageDescription("stringdist")$Version != "0.9.17") stop("expected stringdist 0.9.17")
options(sd_num_thread = 1L)

flat_q <- function(x) {
  if (length(x) == 0) return(numeric(0))
  as.numeric(x)
}

fp_colnames <- function(x) {
  n <- colnames(x)
  if (is.null(n)) return(c(0, 0))
  c(
    length(n),
    sum(vapply(n, function(s) sum(utf8ToInt(s)), numeric(1)))
  )
}

one <- function() {
  c(
    flat_q(qgrams("a", "b", q = 1)),
    flat_q(qgrams("aa", q = 1)),
    flat_q(qgrams(c("a", "a"), q = 1)),
    flat_q(qgrams(c(NA, "a"), q = 1)),
    flat_q(qgrams(NA, q = 1)),
    flat_q(qgrams(c("a", "ab"), q = 2)),
    flat_q(qgrams(c("a"), q = 2)),
    flat_q(qgrams(c(""), q = 0)),
    flat_q(qgrams("Mot\u00f6rhead", "Motorhead", q = 2)),
    flat_q(qgrams("Mot\u00f6rhead", "Motorhead", q = 2, useBytes = TRUE, useNames = TRUE)),
    fp_colnames(qgrams("Mot\u00f6rhead", "Motorhead", q = 2, useBytes = TRUE, useNames = TRUE)),
    flat_q(qgrams("abc", "cba", q = 2, useNames = TRUE)),
    fp_colnames(qgrams("abc", "cba", q = 2, useNames = TRUE)),
    c(nrow(qgrams()), ncol(qgrams())),
    c(nrow(qgrams(NA, q = 1)), ncol(qgrams(NA, q = 1)))
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
