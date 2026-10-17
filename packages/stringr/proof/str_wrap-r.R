.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("stringr")) == "1.6.0")
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
options(warn = 1)

ex <- capture.output({
thanks_path <- file.path(R.home("doc"), "THANKS")
thanks <- str_c(readLines(thanks_path), collapse = "\n")
thanks <- word(thanks, 1, 3, fixed("\n\n"))
cat(str_wrap(thanks), "\n")
cat(str_wrap(thanks, width = 40), "\n")
cat(str_wrap(thanks, width = 60, indent = 2), "\n")
cat(str_wrap(thanks, width = 60, exdent = 2), "\n")
cat(str_wrap(thanks, width = 0, exdent = 2), "\n")
})
writeLines(ex, "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_wrap-r.txt")

one <- function() {
  list(
    blank = str_wrap(c("", " ", "  a  ")),
    zero = str_wrap("a b c d e", 0),
    slash = str_wrap("a/b", width = 0, whitespace_only = FALSE),
    space = str_wrap("a/b", width = 0, whitespace_only = TRUE),
    indent = str_wrap("one two three four", width = 10, indent = 2, exdent = 1),
    na = str_wrap(c("hello world there", NA), width = 8),
    empty = str_wrap(character(0))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0(as.character(toJSON(list(value = value, median_ms = unbox(median(elapsed) * 1000)), auto_unbox = FALSE, na = "null", digits = 16)), "\n"))
