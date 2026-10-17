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

fixture <- "proof/fixtures/sample.hex"

one <- function() {
  list(
    rgb = readhex(fixture),
    hsv = readhex(fixture, "HSV"),
    lab = readhex(fixture, "LAB")
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

dir.create("docs/output", recursive = TRUE, showWarnings = FALSE)
writeLines(capture.output(print(readhex(fixture))), "docs/output/readhex-r.txt")

cat(sprintf(
  '{"rgb":%s,"hsv":%s,"lab":%s,"median_ms":%.17g}\n',
  json_color(value$rgb),
  json_color(value$hsv),
  json_color(value$lab),
  median(elapsed) * 1000
))
