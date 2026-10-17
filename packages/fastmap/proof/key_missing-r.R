.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(fastmap))
if (packageDescription("fastmap")$Version != "1.2.0") stop("expected fastmap 1.2.0")

one <- function() {
  x <- key_missing()
  text <- paste0(capture.output(x), collapse = "\n")
  c(
    as.numeric(is.key_missing(x)),
    as.numeric(identical(x, key_missing())),
    nchar(text),
    utf8ToInt(text)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- sprintf("%.17g", value)
writeLines(
  sprintf(
    "{\"value\":[%s],\"median_ms\":%.17g}\n",
    paste(parts, collapse = ","),
    median(elapsed) * 1000
  ),
  con = "proof/key_missing-r.txt"
)

x <- key_missing()
example <- paste0(
  capture.output(x), "\n",
  "is ", is.key_missing(x), "\n",
  "identical ", identical(x, key_missing()), "\n"
)
cat(paste0(example, collapse = ""), file = "docs/output/key_missing-r.txt")
