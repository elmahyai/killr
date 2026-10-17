suppressPackageStartupMessages(library(SparseM))
suppressPackageStartupMessages(library(e1071))

one <- function() {
  m <- matrix(c(1, 2, 0, 0, 3, 4, 0, 0), 2, 4)
  y <- factor(c("A", "B"))
  path <- tempfile(fileext = ".dat")
  write.matrix.csr(m, path, y = y, fac = TRUE)
  paste(readLines(path), collapse = "\n")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
json_text <- function(x) {
  parts <- strsplit(x, "\n", fixed = TRUE)[[1]]
  parts <- vapply(
    parts,
    function(part) {
      part <- gsub("\\", "\\\\", part, fixed = TRUE)
      gsub("\"", "\\\"", part, fixed = TRUE)
    },
    character(1)
  )
  paste0("\"", paste(parts, collapse = "\\n"), "\"")
}
cat(sprintf(
  '{"text":%s,"median_ms":%.17g}\n',
  json_text(value),
  median(elapsed) * 1000
))
