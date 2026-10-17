suppressPackageStartupMessages(library(colorspace))
stopifnot(identical(packageDescription("colorspace")$Version, "2.1-4"))

json_str <- function(s) {
  if (length(s) != 1L) stop("json_str expects length 1")
  if (is.na(s)) return("null")
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  paste0('"', s, '"')
}
json_vec_chr <- function(x) {
  paste0("[", paste(vapply(x, json_str, ""), collapse = ","), "]")
}
json_rows <- function(m) {
  parts <- character(nrow(m))
  for (i in seq_len(nrow(m))) {
    cells <- vapply(m[i, ], function(v) {
      if (is.na(v) || identical(v, "transparent")) "null" else json_str(v)
    }, "")
    parts[[i]] <- paste0("[", paste(cells, collapse = ","), "]")
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
json_matrix <- function(m) {
  paste0(
    "{",
    '"rownames":', json_vec_chr(rownames(m)), ",",
    '"colnames":', json_vec_chr(colnames(m)), ",",
    '"rows":', json_rows(m),
    "}"
  )
}

out_dir <- file.path("docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
svg(file.path(out_dir, "swatchplot-r.svg"), width = 7, height = 5)
swatchplot(
  "Hue" = sequential_hcl(5, h = c(0, 300), c = c(60, 60), l = 65),
  "Chroma" = sequential_hcl(5, h = 0, c = c(100, 0), l = 65, rev = TRUE, power = 1),
  "Luminance" = sequential_hcl(5, h = 260, c = c(25, 25), l = c(25, 90), rev = TRUE, power = 1),
  off = 0
)
invisible(capture.output(dev.off()))

one <- function() {
  swatchplot(
    "Hue" = sequential_hcl(5, h = c(0, 300), c = c(60, 60), l = 65),
    "Chroma" = sequential_hcl(5, h = 0, c = c(100, 0), l = 65, rev = TRUE, power = 1),
    "Luminance" = sequential_hcl(5, h = 260, c = c(25, 25), l = c(25, 90), rev = TRUE, power = 1),
    off = 0
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
  '{"matrix":%s,"median_ms":%.17g}\n',
  json_matrix(value),
  median(elapsed) * 1000
))
