suppressPackageStartupMessages(library(colorspace))
stopifnot(identical(packageDescription("colorspace")$Version, "2.1-4"))

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
json_mats <- function(ms) {
  paste0("[", paste(vapply(ms, json_mat, ""), collapse = ","), "]")
}

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- sub("^--file=", "", file_arg[[1L]])
out_dir <- file.path(normalizePath(file.path(dirname(script), "..")), "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
writeLines(
  capture.output(interpolate_cvd_transform(tritanomaly_cvd, severity = 0.6)),
  file.path(out_dir, "interpolate_cvd_transform-r.txt")
)

steps <- (0:100) / 100

one <- function() {
  list(
    example = interpolate_cvd_transform(tritanomaly_cvd, 0.6),
    zero = interpolate_cvd_transform(tritanomaly_cvd, 0),
    full = interpolate_cvd_transform(tritanomaly_cvd, 1),
    above = interpolate_cvd_transform(protanomaly_cvd, 1.5),
    below = interpolate_cvd_transform(protanomaly_cvd, -0.2),
    mid = interpolate_cvd_transform(protanomaly_cvd, 0.5),
    quarter = interpolate_cvd_transform(protanomaly_cvd, 0.25),
    three_tenths = interpolate_cvd_transform(deutanomaly_cvd, 0.3),
    third = interpolate_cvd_transform(deutanomaly_cvd, 1/3),
    frac = interpolate_cvd_transform(tritanomaly_cvd, 0.55),
    bulk_tritan = lapply(steps, function(s) interpolate_cvd_transform(tritanomaly_cvd, s)),
    bulk_protan = lapply(steps, function(s) interpolate_cvd_transform(protanomaly_cvd, s)),
    bulk_deutan = lapply(steps, function(s) interpolate_cvd_transform(deutanomaly_cvd, s))
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
    '{"example":%s,"zero":%s,"full":%s,"above":%s,"below":%s,',
    '"mid":%s,"quarter":%s,"three_tenths":%s,"third":%s,"frac":%s,',
    '"bulk_tritan":%s,"bulk_protan":%s,"bulk_deutan":%s,"median_ms":%.17g}\n'
  ),
  json_mat(value$example),
  json_mat(value$zero),
  json_mat(value$full),
  json_mat(value$above),
  json_mat(value$below),
  json_mat(value$mid),
  json_mat(value$quarter),
  json_mat(value$three_tenths),
  json_mat(value$third),
  json_mat(value$frac),
  json_mats(value$bulk_tritan),
  json_mats(value$bulk_protan),
  json_mats(value$bulk_deutan),
  median(elapsed) * 1000
))
