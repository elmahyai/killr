suppressPackageStartupMessages(library(stringdist))
if (packageDescription("stringdist")$Version != "0.9.17") stop("expected stringdist 0.9.17")
options(sd_num_thread = 1L)

one <- function() {
  words <- c("ca", "abc", "MARTHA", "MATHRA", "survey", "surgery", "leia", "leela")
  cross <- numeric(0)
  for (i in seq_len(4L)) {
    left <- words[[i]]
    right <- words[[i + 1L]]
    cross <- c(
      cross,
      seq_dist(list(utf8ToInt(left)), list(utf8ToInt(right)), method = "osa"),
      stringdist(left, right, method = "osa"),
      as.numeric(amatch(left, right, maxDist = 100, method = "osa"))
    )
  }
  c(
    seq_dist(list(c(1L, 1L, 2L)), list(c(1L, 2L, 1L), c(2L, 3L, 1L, 2L))),
    seq_dist(a = list(c(1L, 2L, 3L)), b = list(c(2L, 1L, 3L)), method = "osa"),
    seq_dist(a = list(c(1L, 2L, 3L)), b = list(c(2L, 1L, 3L)), method = "lv"),
    seq_dist(a = list(c(2L, 1L)), b = list(c(1L, 3L, 2L)), method = "dl"),
    seq_dist(a = list(c(1L, 2L, 3L)), b = list(c(1L, 0L, 3L)), method = "hamming"),
    seq_dist(a = list(c(1L, 2L, 3L)), b = list(c(1L, 0L, 3L)), method = "lcs"),
    seq_dist(a = list(c(1L, 2L, 3L)), b = list(c(1L, 0L, 3L)), method = "qgram", q = 2),
    seq_dist(a = list(c(1L, 2L, 3L)), b = list(c(1L, 0L, 3L)), method = "cosine", q = 2),
    seq_dist(a = list(c(1L, 2L, 3L)), b = list(c(1L, 0L, 3L)), method = "jaccard", q = 2),
    round(
      1 - seq_dist(
        list(utf8ToInt("martha")),
        list(utf8ToInt("marhta")),
        method = "jw"
      ),
      3
    ),
    seq_dist(c(1, 2, 3), c(2, 3, 4)),
    seq_dist(list(c(1, 2, 3)), list(c(2, 3, 4))),
    seq_dist(c(3.14, 1), c(3, 1)),
    seq_dist(list(NA_integer_), list(c(1L, 2L))),
    seq_dist(list(c(1L, NA_integer_, 3L)), list(c(1L, 2L, 3L))),
    seq_dist(list(c(1L, 2L)), list(c(1L, 2L, 3L), c(4L, 5L, 6L))),
    seq_dist(list(c(1L, 2L, 3L)), list(c(2L, 1L, 3L)), weight = c(0.5, 1, 1, 1)),
    cross
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
