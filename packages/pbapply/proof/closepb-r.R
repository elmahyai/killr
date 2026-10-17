suppressPackageStartupMessages(library(pbapply))
stopifnot(packageVersion("pbapply") == "1.7-5")
stopifnot(packageDescription("pbapply")$Version == "1.7-5")

closed_flag <- function(pb) {
  as.numeric(!inherits(try(isOpen(pb), silent = TRUE), "try-error"))
}

one <- function() {
  out <- numeric(0)
  opb <- pboptions(
    type = "timer",
    style = 3,
    char = "+",
    txt.width = 50,
    initial = 0,
    min_time = 0
  )
  for (p in list(c(0, 10), c(2, 5))) {
    pb <- startpb(p[[1]], p[[2]])
    setpb(pb, p[[1]] + 3)
    out <- c(out, getpb(pb))
    closepb(pb)
    out <- c(out, closed_flag(pb))
  }
  closepb(NULL)
  out <- c(out, 0)
  pboptions(type = "none")
  closepb(startpb(0, 1))
  out <- c(out, 0)
  pboptions(type = "txt")
  pb <- startpb(0, 5)
  setpb(pb, 2)
  out <- c(out, getpb(pb))
  closepb(pb)
  out <- c(out, closed_flag(pb))
  pboptions(opb)
  out
}

quiet_one <- function() {
  capture.output(one(), type = "output")
  invisible(NULL)
}

value <- {
  capture.output(v <- one(), type = "output")
  v
}
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  quiet_one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- vapply(value, function(x) if (is.na(x)) "null" else sprintf("%.17g", x), "")
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(parts, collapse = ","),
  median(elapsed) * 1000
))
