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
  if (length(m) == 0) return("[]")
  parts <- character(nrow(m))
  for (i in seq_len(nrow(m))) {
    parts[[i]] <- paste0(
      "[", paste(vapply(m[i, ], json_num, ""), collapse = ","), "]"
    )
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
json_color <- function(obj) {
  cols <- colnames(obj@coords)
  if (is.null(cols)) cols <- character(0)
  sprintf(
    '{"space":%s,"names":%s,"columns":[%s],"coords":%s}',
    json_str(class(obj)[[1L]]),
    json_names(rownames(obj@coords)),
    paste(vapply(cols, json_str, ""), collapse = ","),
    json_mat(obj@coords)
  )
}

matrix_hcl <- matrix(
  c(50, 50, 50, 80, 80, 80, 0, 180, 360),
  ncol = 3,
  dimnames = list(c("a", "b", "c"), NULL)
)

one <- function() {
  list(
    channels = polarLUV(seq(0, 100, length.out = 13)[-13], 80, 0),
    matrix = polarLUV(matrix_hcl),
    empty = polarLUV()
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
    '{"channels":%s,"matrix":%s,"empty":%s,"median_ms":%.17g}\n'
  ),
  json_color(value$channels),
  json_color(value$matrix),
  json_color(value$empty),
  median(elapsed) * 1000
))
