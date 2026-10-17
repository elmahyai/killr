suppressPackageStartupMessages(library(tools))

one <- function() {
  dir <- tempfile("vig")
  dir.create(dir)
  writeLines(c(
    "% \\VignetteIndexEntry{A Title}",
    "% \\VignetteDepends{foo, bar}",
    "% \\VignetteKeywords{one, two}",
    "% \\VignetteEngine{knitr::knitr}"
  ), file.path(dir, "demo.Rnw"))
  writeLines("nothing", file.path(dir, "empty.Rnw"))
  a <- vignetteInfo(file.path(dir, "demo.Rnw"))
  b <- vignetteInfo(file.path(dir, "empty.Rnw"))
  paste0(
    "VIG ", a$file, " ", a$title, " ", paste(a$depends, collapse=","), " ",
    paste(a$keywords, collapse=","), " ", a$engine, "\n",
    "VIG0 ", b$title, " ", paste(b$depends, collapse=","), " ",
    paste(b$keywords, collapse=","), " ", b$engine, "\n"
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
