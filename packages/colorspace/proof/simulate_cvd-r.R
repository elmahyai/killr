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
json_vec <- function(x) {
  paste0("[", paste(vapply(x, json_str, ""), collapse = ","), "]")
}
json_num <- function(x) sprintf("%.17g", x)
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
    '{"space":%s,"names":null,"columns":[%s],"coords":%s}',
    json_str(class(obj)[[1L]]),
    paste(vapply(colnames(obj@coords), json_str, ""), collapse = ","),
    json_mat(obj@coords)
  )
}

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- sub("^--file=", "", file_arg[[1L]])
out_dir <- file.path(normalizePath(file.path(dirname(script), "..")), "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
example_col <- c("#005000", "blue", "#00BB00")
writeLines(
  capture.output(simulate_cvd(example_col, tritanomaly_cvd["6"][[1]])),
  file.path(out_dir, "simulate_cvd-r.txt")
)

rgb_mat <- diag(3) * 255
rownames(rgb_mat) <- c("R", "G", "B")
wide <- matrix(
  c(255, 0, 0, 0, 255, 0, 0, 0, 255, 128, 64, 32),
  ncol = 3,
  byrow = TRUE
)
colnames(wide) <- c("R", "G", "B")
srgb_obj <- sRGB(c(1, 0, 0.25), c(0, 1, 0.5), c(0, 0, 0.75))
lab_obj <- LAB(c(50, 60, 70), c(40, -20, 10), c(30, 50, -40))
hexes <- c("#FF0000", "#00FF0080", "#336699", "#AABBCCDD")
bulk <- sprintf("#%02X%02X%02X", 0:255, 255:0, (0:255 + 17) %% 256)

one <- function() {
  list(
    example = simulate_cvd(example_col, tritanomaly_cvd["6"][[1]]),
    interpolated = simulate_cvd(
      example_col,
      interpolate_cvd_transform(tritanomaly_cvd, severity = 0.6)
    ),
    hex = simulate_cvd("#33ab20", tritanomaly_cvd[["6"]]),
    named = simulate_cvd("red", deutanomaly_cvd[["8"]]),
    mixed = simulate_cvd(c("green", "#ffc0cb"), protanomaly_cvd[["8"]]),
    alpha = simulate_cvd(hexes, protanomaly_cvd[["10"]]),
    palette = simulate_cvd(1:3, tritanomaly_cvd[["4"]]),
    linear_false = simulate_cvd(
      c("#FF0000", "#800080", "#FFA500"),
      tritanomaly_cvd[["10"]],
      linear = FALSE
    ),
    rgb_matrix = simulate_cvd(rgb_mat, deutanomaly_cvd[["6"]]),
    wide = simulate_cvd(wide, protanomaly_cvd[["3"]]),
    srgb_object = simulate_cvd(srgb_obj, tritanomaly_cvd[["6"]]),
    lab_object = simulate_cvd(lab_obj, tritanomaly_cvd[["7"]]),
    lab_gamma = simulate_cvd(lab_obj, tritanomaly_cvd[["7"]], linear = FALSE),
    bulk = simulate_cvd(bulk, tritanomaly_cvd[["6"]])
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
    '{"example":%s,"interpolated":%s,"hex":%s,"named":%s,"mixed":%s,',
    '"alpha":%s,"palette":%s,"linear_false":%s,"rgb_matrix":%s,"wide":%s,',
    '"srgb_object":%s,"lab_object":%s,"lab_gamma":%s,"bulk":%s,',
    '"median_ms":%.17g}\n'
  ),
  json_vec(unname(value$example)),
  json_vec(unname(value$interpolated)),
  json_vec(unname(value$hex)),
  json_vec(unname(value$named)),
  json_vec(unname(value$mixed)),
  json_vec(unname(value$alpha)),
  json_vec(unname(value$palette)),
  json_vec(unname(value$linear_false)),
  json_mat(value$rgb_matrix),
  json_mat(value$wide),
  json_color(value$srgb_object),
  json_color(value$lab_object),
  json_color(value$lab_gamma),
  json_vec(unname(value$bulk)),
  median(elapsed) * 1000
))
