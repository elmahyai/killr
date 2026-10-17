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
json_rows <- function(x) {
  rows <- character()
  for (lang in names(x)) {
    comps <- x[[lang]]
    for (nm in names(comps)) {
      rows <- c(rows, paste0("[", json_str(lang), ", ", json_str(nm), ", ", json_str(comps[[nm]]), "]"))
    }
  }
  paste0("[", paste(rows, collapse = ", "), "]")
}
one <- function() all_patterns
value <- one()
writeLines(
  paste0(
    "all_patterns$rnw chunk.begin is ", value$rnw$chunk.begin,
    " and all_patterns$html header.begin is ", value$html$header.begin,
    "; str(all_patterns) is a list of ", length(value), "."
  ),
  "/home/ahmed/killr_projects/killr/packages/knitr/docs/output/all_patterns-r.txt"
)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_rows(value), median(elapsed) * 1000))
