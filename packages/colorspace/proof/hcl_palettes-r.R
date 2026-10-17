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
json_vec_num <- function(x) {
  parts <- vapply(x, function(v) {
    if (is.na(v)) "null" else format(v, digits = 17, scientific = TRUE)
  }, "")
  paste0("[", paste(parts, collapse = ","), "]")
}
json_vec_logi <- function(x) {
  parts <- vapply(x, function(v) if (is.na(v)) "null" else if (v) "true" else "false", "")
  paste0("[", paste(parts, collapse = ","), "]")
}

frame_to_json <- function(pals) {
  paste0(
    "{",
    '"names":', json_vec_chr(rownames(pals)), ",",
    '"type":', json_vec_chr(as.character(pals$type)), ",",
    '"h1":', json_vec_num(pals$h1), ",",
    '"h2":', json_vec_num(pals$h2), ",",
    '"c1":', json_vec_num(pals$c1), ",",
    '"c2":', json_vec_num(pals$c2), ",",
    '"l1":', json_vec_num(pals$l1), ",",
    '"l2":', json_vec_num(pals$l2), ",",
    '"p1":', json_vec_num(pals$p1), ",",
    '"p2":', json_vec_num(pals$p2), ",",
    '"cmax":', json_vec_num(pals$cmax), ",",
    '"fixup":', json_vec_logi(pals$fixup),
    "}"
  )
}

one <- function() {
  list(
    qualitative = hcl_palettes(type = "Qualitative"),
    set2 = hcl_palettes(palette = "Set 2"),
    mixed = hcl_palettes(type = c("seq", "div"), palette = c("blues", "tropic")),
    print_set2 = capture.output(print(hcl_palettes(palette = "Set 2")))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

OUTPUT <- file.path("docs", "output")
dir.create(OUTPUT, recursive = TRUE, showWarnings = FALSE)
svg_path <- file.path(OUTPUT, "hcl_palettes-r.svg")
suppressMessages({
  grDevices::svg(svg_path, width = 8, height = 10)
  invisible(hcl_palettes(type = "Qualitative", plot = TRUE, n = 7))
  invisible(grDevices::dev.off())
})
writeLines(value$print_set2, file.path(OUTPUT, "hcl_palettes-set2-r.txt"))

cat(sprintf(
  paste0(
    '{"qualitative":%s,"set2":%s,"mixed":%s,',
    '"print_set2":%s,"median_ms":%.17g}\n'
  ),
  frame_to_json(value$qualitative),
  frame_to_json(value$set2),
  frame_to_json(value$mixed),
  json_vec_chr(value$print_set2),
  median(elapsed) * 1000
))
