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

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- sub("^--file=", "", file_arg[[1L]])
out_dir <- file.path(normalizePath(file.path(dirname(script), "..")), "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
writeLines(capture.output(protanomaly_cvd), file.path(out_dir, "protanomaly_cvd-r.txt"))

one <- function() {
  tables <- protanomaly_cvd
  names <- names(tables)
  matrices <- lapply(names, function(k) as.matrix(tables[[k]]))
  list(names = names, matrices = matrices)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

mat_json <- paste0(
  "[",
  paste(vapply(value$matrices, function(m) json_mat(m), ""), collapse = ","),
  "]"
)

cat(sprintf(
  '{"names":%s,"matrices":%s,"median_ms":%.17g}\n',
  json_vec(value$names),
  mat_json,
  median(elapsed) * 1000
))
