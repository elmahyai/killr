suppressPackageStartupMessages(library(pbapply))
stopifnot(packageVersion("pbapply") == "1.7-5")
stopifnot(packageDescription("pbapply")$Version == "1.7-5")

one <- function() {
  pairs <- list(c(0, 1), c(0, 10), c(2, 5), c(-10, 10))
  out <- numeric(0)
  opb <- pboptions(
    type = "timer",
    style = 3,
    char = "+",
    txt.width = 50,
    initial = 0,
    min_time = 0
  )
  for (p in pairs) {
    pb <- startpb(p[[1]], p[[2]])
    out <- c(out, if (is.null(pb)) NA_real_ else getpb(pb))
    closepb(pb)
  }
  pboptions(initial = 0.25)
  pb <- startpb(0, 10)
  out <- c(out, getpb(pb))
  closepb(pb)
  pboptions(type = "none")
  pb <- startpb(0, 1)
  out <- c(out, if (is.null(pb)) NA_real_ else getpb(pb))
  closepb(pb)
  pboptions(opb)
  out
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- vapply(value, function(x) if (is.na(x)) "null" else sprintf("%.17g", x), "")
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(parts, collapse = ","),
  median(elapsed) * 1000
))
