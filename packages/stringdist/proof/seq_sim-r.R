suppressPackageStartupMessages(library(stringdist))
if (packageDescription("stringdist")$Version != "0.9.17") stop("expected stringdist 0.9.17")
options(sd_num_thread = 1L)

one <- function() {
  L1 <- list(c(1L, NA_integer_, 3L), 2:4, NA_integer_)
  L2 <- list(1:3)
  c(
    seq_sim(L1, L2),
    seq_sim(list(c(1L, 1L, 2L)), list(c(1L, 2L, 1L), c(2L, 3L, 1L, 2L))),
    seq_sim(a = list(c(1L, 2L, 3L)), b = list(c(2L, 1L, 3L)), method = "osa"),
    seq_sim(a = list(c(1L, 2L, 3L)), b = list(c(2L, 1L, 3L)), method = "lv"),
    seq_sim(a = list(c(2L, 1L)), b = list(c(1L, 3L, 2L)), method = "dl"),
    seq_sim(a = list(c(1L, 2L, 3L)), b = list(c(1L, 0L, 3L)), method = "hamming"),
    seq_sim(a = list(c(1L, 2L, 3L)), b = list(c(1L, 0L, 3L)), method = "lcs"),
    seq_sim(a = list(c(1L, 2L, 3L)), b = list(c(1L, 0L, 3L)), method = "qgram", q = 2),
    seq_sim(a = list(c(1L, 2L, 3L)), b = list(c(1L, 0L, 3L)), method = "cosine", q = 2),
    seq_sim(a = list(c(1L, 2L, 3L)), b = list(c(1L, 0L, 3L)), method = "jaccard", q = 2),
    round(
      seq_sim(
        list(utf8ToInt("martha")),
        list(utf8ToInt("marhta")),
        method = "jw"
      ),
      3
    ),
    seq_sim(list(c(1, 2, 3)), list(c(2, 3, 4))),
    seq_sim(list(c(3.14, 1)), list(c(3, 1))),
    seq_sim(list(NA_integer_), list(c(1L, 2L))),
    seq_sim(list(c(1L, NA_integer_, 3L)), list(c(1L, 2L, 3L))),
    seq_sim(list(c(1L, 2L)), list(c(1L, 2L, 3L), c(4L, 5L, 6L))),
    seq_sim(list(c(1L, 2L, 3L)), list(c(2L, 1L, 3L)), weight = c(0.5, 1, 1, 1))
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
