suppressPackageStartupMessages(library(stringi))
stopifnot(identical(as.character(packageVersion("stringi")), "1.8.9"))

json_str <- function(x) {
  if (is.na(x)) return("null")
  chars <- utf8ToInt(enc2utf8(x))
  if (length(chars) == 0) return("\"\"")
  parts <- character(length(chars))
  for (i in seq_along(chars)) {
    cp <- chars[[i]]
    parts[[i]] <- if (cp == 34L) "\\\""
      else if (cp == 92L) "\\\\"
      else if (cp == 10L) "\\n"
      else if (cp == 13L) "\\r"
      else if (cp == 9L) "\\t"
      else if (cp < 32L || cp == 127L || cp > 126L) sprintf("\\u%04x", cp)
      else intToUtf8(cp)
  }
  paste0('"', paste(parts, collapse = ""), '"')
}

json_lgl <- function(x) {
  if (is.na(x)) "null" else if (isTRUE(x)) "true" else "false"
}

one <- function() stri_trans_isnfkc(c("fi", "\ufb01", NA_character_, ""))

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
encoded <- if (is.character(value)) vapply(value, json_str, "") else vapply(value, json_lgl, "")
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(encoded, collapse = ","),
  median(elapsed) * 1000
))

cmd <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", cmd, value = TRUE)
script <- substring(file_arg[[1]], 8)
out_path <- file.path(dirname(dirname(normalizePath(script))), "docs", "output", "stri_trans_isnfkc-r.txt")
dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)
writeLines(paste0(
  "stri_trans_isnfkc of the fi ligature returns ",
  stri_trans_isnfkc("\ufb01"),
  "."
), out_path)
