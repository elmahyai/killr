suppressPackageStartupMessages(library(pbapply))
stopifnot(packageVersion("pbapply") == "1.7-5")
stopifnot(packageDescription("pbapply")$Version == "1.7-5")

one <- function() {
  opb <- pboptions(type = "none")
  on.exit(pboptions(opb), add = TRUE)
  z <- list(a = 1, b = 2, c = 3)
  acc <- 0
  pbwalk(z, function(x) {
    acc <<- acc + x
  })
  c(
    acc,
    as.numeric(unlist(invisible(pbwalk(list(10, 20), sum))))
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
