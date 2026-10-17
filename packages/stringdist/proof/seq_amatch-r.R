suppressPackageStartupMessages(library(stringdist))
if (packageDescription("stringdist")$Version != "0.9.17") stop("expected stringdist 0.9.17")
options(sd_num_thread = 1L)

one <- function() {
  x <- list(1:3, c(3:1), c(1L, 3L, 4L))
  table <- list(c(5L, 3L, 1L, 2L), 1:4)
  c(
    as.numeric(seq_amatch(x, table, maxDist = 2)),
    as.numeric(seq_amatch(x, table, maxDist = 0.5)),
    as.numeric(seq_amatch(list(c(1L, 2L, 3L)), list(c(2L, 1L, 3L)), method = "osa", maxDist = 2)),
    as.numeric(seq_amatch(list(c(1L, 2L, 3L)), list(c(2L, 1L, 3L)), method = "lv", maxDist = 2)),
    as.numeric(seq_amatch(list(c(2L, 1L)), list(c(1L, 3L, 2L)), method = "dl", maxDist = 3)),
    as.numeric(seq_amatch(list(c(1L, 2L, 3L)), list(c(1L, 0L, 3L)), method = "hamming", maxDist = 2)),
    as.numeric(seq_amatch(list(c(1L, 2L, 3L)), list(c(1L, 0L, 3L)), method = "lcs", maxDist = 2)),
    as.numeric(seq_amatch(list(c(1L, 2L, 3L)), list(c(1L, 0L, 3L)), method = "qgram", q = 2, maxDist = 1)),
    as.numeric(seq_amatch(list(c(1L, 2L, 3L)), list(c(1L, 0L, 3L)), method = "cosine", q = 2, maxDist = 1)),
    as.numeric(seq_amatch(list(c(1L, 2L, 3L)), list(c(1L, 0L, 3L)), method = "jaccard", q = 2, maxDist = 1)),
    as.numeric(
      seq_amatch(
        list(utf8ToInt("martha")),
        list(utf8ToInt("marhta")),
        method = "jw",
        maxDist = 0.2
      )
    ),
    as.numeric(seq_amatch(list(c(1L, 2L, 3L)), list(c(2L, 3L, 4L)), maxDist = 2)),
    as.numeric(seq_amatch(list(c(3.14, 1)), list(c(3L, 1L)), maxDist = 1)),
    as.numeric(seq_amatch(list(NA_integer_), list(c(1L, 2L)), maxDist = 2)),
    as.numeric(
      seq_amatch(
        list(c(1L, NA_integer_, 3L), NA_integer_),
        list(1:3),
        maxDist = 1
      )
    ),
    as.numeric(
      seq_amatch(
        list(c(1L, NA_integer_, 3L), NA_integer_),
        list(1:3),
        maxDist = 1,
        matchNA = FALSE
      )
    ),
    as.numeric(seq_amatch(list(c(1L, 2L)), list(c(1L, 2L, 3L), c(4L, 5L, 6L)), maxDist = 1)),
    as.numeric(seq_amatch(list(c(1L, 2L, 3L)), list(c(2L, 1L, 3L)), maxDist = Inf)),
    as.numeric(
      seq_amatch(
        list(c(1L, 2L, 3L)),
        list(c(2L, 1L, 3L)),
        weight = c(0.5, 1, 1, 1),
        maxDist = 2
      )
    ),
    as.numeric(
      seq_amatch(
        list(c(1L, 2L)),
        list(c(1L, 2L, 3L), c(4L, 5L, 6L)),
        maxDist = 1,
        nomatch = 0
      )
    )
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
  paste(vapply(value, fmt, character(1)), collapse = ","),
  stats::median(elapsed) * 1000
))
