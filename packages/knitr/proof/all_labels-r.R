suppressPackageStartupMessages(library(knitr))
stopifnot(as.character(packageVersion("knitr")) == "1.52")
json_str <- function(s) {
  if (is.na(s)) return("null")
  chars <- strsplit(enc2utf8(s), "", fixed = TRUE)[[1]]
  parts <- character(length(chars))
  for (i in seq_along(chars)) {
    cp <- utf8ToInt(chars[[i]])
    parts[[i]] <- if (cp == 34) paste0("\\", '"')
      else if (cp == 92) paste0("\\", "\\")
      else if (cp == 10) paste0("\\", "n")
      else if (cp == 13) paste0("\\", "r")
      else if (cp == 9) paste0("\\", "t")
      else if (cp < 32 || cp == 127) sprintf("\\u%04x", cp)
      else chars[[i]]
  }
  paste0('"', paste(parts, collapse = ""), '"')
}
json_vec <- function(x) {
  if (is.null(x)) return("null")
  if (length(x) == 0L) return("[]")
  parts <- character(length(x))
  for (i in seq_along(x)) {
    if (is.na(x[[i]])) parts[[i]] <- "null" else parts[[i]] <- json_str(x[[i]])
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
knit_code$restore()
knit_code$set(
  a = structure("x", chunk_opts = list(engine = "R", echo = TRUE, results = "markup")),
  b = structure("y", chunk_opts = list(engine = "Rcpp", echo = FALSE, results = "markup")),
  c = structure("z", chunk_opts = list(engine = "R", echo = FALSE, results = "hide"))
)
one <- function() all_labels(echo == FALSE, results != "hide")
value <- one()
writeLines(
  paste0(
    "all_labels(echo == FALSE, results != \"hide\") returns ",
    paste(value, collapse = ", "),
    "."
  ),
  "/home/ahmed/killr_projects/killr/packages/knitr/docs/output/all_labels-r.txt"
)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_vec(value), median(elapsed) * 1000))
