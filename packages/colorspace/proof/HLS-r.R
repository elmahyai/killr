suppressPackageStartupMessages(library(colorspace))
stopifnot(identical(packageDescription("colorspace")$Version, "2.1-4"))

json_num <- function(x) sprintf("%.17g", x)
json_str <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  paste0('"', s, '"')
}
json_names <- function(nm) {
  if (is.null(nm)) return("null")
  paste0("[", paste(vapply(nm, json_str, ""), collapse = ","), "]")
}
json_mat <- function(m) {
  parts <- character(nrow(m))
  for (i in seq_len(nrow(m))) {
    parts[[i]] <- paste0(
      "[", paste(vapply(m[i, ], json_num, ""), collapse = ","), "]"
    )
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
json_color <- function(obj) {
  sprintf(
    '{"space":%s,"names":%s,"columns":[%s],"coords":%s}',
    json_str(class(obj)[[1L]]),
    json_names(rownames(obj@coords)),
    paste(vapply(colnames(obj@coords), json_str, ""), collapse = ","),
    json_mat(obj@coords)
  )
}

matrix_hls <- matrix(
  c(0, 30, 60, 0.5, 0.5, 0.5, 1, 1, 1),
  ncol = 3,
  dimnames = list(c("a", "b", "c"), NULL)
)

one <- function() {
  list(
    example = HLS(seq(0, 360, length.out = 13)[-13], 0.5, 1),
    matrix = HLS(matrix_hls),
    named = HLS(c(0, 30, 60), 0.5, 1, names = c("x", "y", "z")),
    integer_h = HLS(as.integer(c(0, 30)), 0.5, 1L),
    scalar = HLS(0.123456789, 0.5, 1),
    empty = HLS(),
    bulk = HLS(seq(0, 360, length.out = 256), 0.5, 1)
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
    '{"example":%s,"matrix":%s,"named":%s,"integer_h":%s,',
    '"scalar":%s,"empty":%s,"bulk":%s,"median_ms":%.17g}\n'
  ),
  json_color(value$example),
  json_color(value$matrix),
  json_color(value$named),
  json_color(value$integer_h),
  json_color(value$scalar),
  json_color(value$empty),
  json_color(value$bulk),
  median(elapsed) * 1000
))
