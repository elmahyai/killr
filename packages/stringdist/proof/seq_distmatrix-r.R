suppressPackageStartupMessages(library(stringdist))
if (packageDescription("stringdist")$Version != "0.9.17") stop("expected stringdist 0.9.17")
options(sd_num_thread = 1L)

column_major <- function(mat) {
  if (length(mat) == 0L) return(numeric(0))
  as.vector(mat)
}

one <- function() {
  seqs <- list(
    c(1L, 2L, 3L),
    c(2L, 3L, 4L),
    c(1L, 2L, 1L),
    c(5L, 6L, 7L, 8L),
    c(1L, 0L, 3L),
    c(2L, 1L),
    c(1L, 3L, 2L),
    c(10L, 11L, 12L)
  )
  short <- seqs[1:4]
  parts <- list(
    column_major(seq_distmatrix(short, short[2:4], method = "osa")),
    column_major(
      seq_distmatrix(short, short[2:4], method = "dl", weight = c(0.5, 0.8, 0.3, 0.4))
    ),
    column_major(seq_distmatrix(short, short[2:4], method = "jw", p = 0.1)),
    column_major(seq_distmatrix(short, short[2:4], method = "cosine", q = 2)),
    column_major(
      seq_distmatrix(list(c(1L, 2L), c(1L, 2L, 3L)), list(c(2L, 1L), c(1L, 2L, 3L)), method = "hamming")
    ),
    column_major(seq_distmatrix(list(NA_integer_, c(1L, 2L)), list(c(1L, 2L), c(3L, 4L)))),
    column_major(seq_distmatrix(list(), list(c(1L, 2L)))),
    as.numeric(seq_distmatrix(short, method = "osa")),
    as.numeric(seq_distmatrix(short[1:3], method = "lcs")),
    column_major(
      seq_distmatrix(
        list(c(1L, 2L, 3L), c(4L, 5L, 6L)),
        list(c(1L, 2L, 3L), c(4L, 5L, 6L)),
        weight = c(0.5, 1, 1, 1)
      )
    ),
    column_major(
      seq_distmatrix(
        list(x = c(1L, 2L, 3L), y = c(2L, 3L, 4L)),
        list(x = c(1L, 2L, 3L), y = c(2L, 3L, 4L)),
        useNames = "names"
      )
    ),
    column_major(seq_distmatrix(list(c(1L, 2L, 3L)), list(c(2L, 3L, 4L)))),
    as.numeric(seq_distmatrix(c(1, 2, 3))),
    column_major(
      seq_distmatrix(
        list(c(1L, NA_integer_, 3L)),
        list(c(1L, 2L, 3L)),
        method = "osa"
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
