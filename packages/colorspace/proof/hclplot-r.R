suppressPackageStartupMessages(library(colorspace))
stopifnot(identical(packageDescription("colorspace")$Version, "2.1-4"))

json_num <- function(x) {
  if (is.na(x)) return("null")
  format(x, digits = 17, scientific = TRUE)
}
matrix_to_json <- function(m) {
  rows <- apply(m, 1L, function(row) {
    paste0("[", paste(vapply(row, json_num, ""), collapse = ","), "]")
  })
  paste0("[", paste(rows, collapse = ","), "]")
}

one <- function() {
  list(
    qual = hclplot(qualitative_hcl(9, c = 50, l = 70), plot = FALSE),
    seq = hclplot(sequential_hcl(7, h = 260, c = 80, l = c(35, 95), power = 1), plot = FALSE),
    div = hclplot(diverging_hcl(7, h = c(260, 0), c = 80, l = c(35, 95), power = 1), plot = FALSE)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

out_dir <- "docs/output"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
invisible(capture.output(suppressMessages({
  grDevices::svg(filename = file.path(out_dir, "hclplot-r.svg"), width = 8, height = 8)
  hclplot(qualitative_hcl(9, c = 50, l = 70))
  grDevices::dev.off()
})))

cat(sprintf(
  '{"qual":%s,"seq":%s,"div":%s,"median_ms":%.17g}\n',
  matrix_to_json(value$qual),
  matrix_to_json(value$seq),
  matrix_to_json(value$div),
  median(elapsed) * 1000
))
