suppressPackageStartupMessages(library(pbapply))
stopifnot(packageVersion("pbapply") == "1.7-5")
stopifnot(packageDescription("pbapply")$Version == "1.7-5")

one <- function() {
  opb <- pboptions(type = "none")
  on.exit(pboptions(opb), add = TRUE)
  X <- 1:12
  INDEX <- list(
    c("a", "a", "a", "a", "b", "b", "b", "b", "c", "c", "c", "c"),
    c(1, 1, 2, 2, 1, 1, 2, 2, 1, 1, 2, 2)
  )
  c(
    as.numeric(pbtapply(X, INDEX, sum)),
    as.numeric(pbtapply(X, INDEX, NULL))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- vapply(value, sprintf, character(1), fmt = "%.17g")
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(parts, collapse = ","),
  median(elapsed) * 1000
))
