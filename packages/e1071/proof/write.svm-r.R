.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(e1071))
if (packageDescription("e1071")$Version != "1.7-17") stop("expected e1071 1.7-17")

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

one <- function() {
  set.seed(4242)
  x <- matrix(
    c(0.0, 1.0, 1.2, 0.8, 2.5, 2.7, 2.8, 2.4, 0.1, 0.9, 2.6, 2.5),
    ncol = 2,
    byrow = TRUE
  )
  y <- factor(c("setosa", "setosa", "versicolor", "versicolor", "setosa", "versicolor"))
  fit <- svm(
    x,
    y,
    scale = TRUE,
    kernel = "radial",
    cost = 1,
    gamma = 0.5,
    probability = FALSE,
    cross = 0
  )
  svm_path <- tempfile(fileext = ".svm")
  scale_path <- tempfile(fileext = ".scale")
  write.svm(fit, svm.file = svm_path, scale.file = scale_path)
  paste(
    c(
      paste(readLines(svm_path), collapse = "\n"),
      paste(readLines(scale_path), collapse = "\n")
    ),
    collapse = "\n---\n"
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
  '{"text":%s,"median_ms":%.17g}\n',
  json_text(value),
  median(elapsed) * 1000
))
