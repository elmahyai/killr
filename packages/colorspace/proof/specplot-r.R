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
  parts <- vapply(x, function(v) if (is.na(v)) "null" else json_str(v), "")
  paste0("[", paste(parts, collapse = ","), "]")
}

json_vec_num <- function(x) {
  parts <- vapply(x, function(v) {
    if (is.na(v)) "null" else format(v, digits = 17, scientific = TRUE)
  }, "")
  paste0("[", paste(parts, collapse = ","), "]")
}

matrix_to_json <- function(m) {
  rows <- apply(m, 1L, function(row) {
    paste0("[", paste(vapply(row, function(v) {
      if (is.na(v)) "null" else format(v, digits = 17, scientific = TRUE)
    }, ""), collapse = ","), "]")
  })
  paste0("[", paste(rows, collapse = ","), "]")
}

result_to_json <- function(r) {
  paste0(
    "{",
    '"HCL":', matrix_to_json(r$HCL), ",",
    '"RGB":', matrix_to_json(r$RGB), ",",
    '"hex":', json_vec_chr(r$hex),
    "}"
  )
}

one <- function() {
  x <- sequential_hcl(50, "Blues 3")
  y <- sequential_hcl(50, "Reds 3")
  list(
    blues = specplot(x, plot = FALSE),
    compare = specplot(x, y = y, rgb = TRUE, plot = FALSE),
    rainbow_hcl100 = specplot(rainbow_hcl(100), fix = TRUE, plot = FALSE),
    na_tail = specplot(c(x[1:10], NA), plot = FALSE),
    nofix = specplot(rainbow_hcl(10), fix = FALSE, plot = FALSE)
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
  grDevices::svg(filename = file.path(out_dir, "specplot-r.svg"), width = 8, height = 6)
  specplot(rainbow(100), rgb = TRUE)
  grDevices::dev.off()
})))

cat(sprintf(
  paste0(
    '{"blues":%s,"compare":%s,"rainbow_hcl100":%s,"na_tail":%s,"nofix":%s,',
    '"median_ms":%.17g}\n'
  ),
  result_to_json(value$blues),
  result_to_json(value$compare),
  result_to_json(value$rainbow_hcl100),
  result_to_json(value$na_tail),
  result_to_json(value$nofix),
  median(elapsed) * 1000
))
