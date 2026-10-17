suppressPackageStartupMessages(library(colorspace))
stopifnot(identical(packageDescription("colorspace")$Version, "2.1-4"))

json_num <- function(x) sprintf("%.17g", x)
json_mat <- function(m) {
  if (length(m) == 0L) return("[]")
  parts <- character(nrow(m))
  for (i in seq_len(nrow(m))) {
    parts[[i]] <- paste0(
      "[", paste(vapply(m[i, ], json_num, ""), collapse = ","), "]"
    )
  }
  paste0("[", paste(parts, collapse = ","), "]")
}

matrix_hls <- matrix(
  c(0, 30, 60, 0.5, 0.5, 0.5, 1, 1, 1),
  ncol = 3,
  dimnames = list(c("a", "b", "c"), NULL)
)

one <- function() {
  list(
    hls = coords(HLS(c(0, 30, 60), 0.5, 1)),
    lab = coords(LAB(c(50, 60), 10, -20)),
    rgb = coords(RGB(c(0.2, 0.4), 0.5, 0.8)),
    matrix_hls = coords(HLS(matrix_hls)),
    empty = coords(HLS())
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

cat(sprintf(
  paste0(
    '{"hls":%s,"lab":%s,"rgb":%s,"matrix_hls":%s,"empty":%s,',
    '"median_ms":%.17g}\n'
  ),
  json_mat(value$hls),
  json_mat(value$lab),
  json_mat(value$rgb),
  json_mat(value$matrix_hls),
  json_mat(value$empty),
  median(elapsed) * 1000
))
