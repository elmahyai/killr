.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")

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

json_val <- function(x) {
  if (is.null(x)) return("null")
  if (is.character(x)) {
    if (length(x) == 0) return("[]")
    return(paste0("[", paste(vapply(x, json_str, ""), collapse = ","), "]"))
  }
  if (is.list(x)) {
    nms <- names(x)
    if (!is.null(nms)) {
      parts <- character(length(x))
      for (i in seq_along(x)) {
        parts[[i]] <- paste0(json_str(nms[[i]]), ":", json_val(x[[i]]))
      }
      return(paste0("{", paste(parts, collapse = ","), "}"))
    }
    if (length(x) == 0) return("[]")
    return(paste0("[", paste(vapply(x, json_val, ""), collapse = ","), "]"))
  }
  stop("unexpected proof value")
}


one <- function() {
  list(
    star = stri_pad_right("ab", 5, pad = "*"),
    wide = stri_pad_right("\u1100", 4),
    na = stri_pad_right(c(NA_character_, "ab", "NA"), 4, pad = "*"),
    short = stri_pad_right("abcd", 2, pad = "*"),
    empty = stri_pad_right("", 3, pad = "*")
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))

cmd <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", cmd, value = TRUE)
script <- substring(file_arg[[1]], 8)
out_path <- file.path(dirname(dirname(normalizePath(script))), "docs", "output", "stri_pad_right-r.txt")
dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)
writeLines('stri_pad_right("ab", 5, "*") returns ab***.', out_path)
