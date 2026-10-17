suppressPackageStartupMessages(library(stringdist))
if (packageDescription("stringdist")$Version != "0.9.17") stop("expected stringdist 0.9.17")
options(sd_num_thread = 1L)

flat_m <- function(x) {
  if (length(x) == 0) return(numeric(0))
  as.numeric(x)
}

one <- function() {
  c(
    flat_m(seq_qgrams(1:3, 2:4, q = 2)),
    flat_m(seq_qgrams(q = 1, 1:2)),
    flat_m(seq_qgrams(c(1L, NA_integer_, 3L), q = 2)),
    flat_m(seq_qgrams(integer(0), 1:2, q = 1)),
    flat_m(seq_qgrams(NA_integer_, q = 1)),
    flat_m(seq_qgrams(1:2, q = 3)),
    c(nrow(seq_qgrams()), ncol(seq_qgrams()))
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
