suppressPackageStartupMessages(library(pbapply))
stopifnot(packageVersion("pbapply") == "1.7-5")
stopifnot(packageDescription("pbapply")$Version == "1.7-5")

run_case <- function(...) {
  out <- numeric(0)
  f <- tempfile()
  on.exit(unlink(f))
  con <- file(f, open = "wt")
  on.exit(close(con), add = TRUE)
  pb <- timerProgressBar(..., file = con)
  out <- c(out, getpb(pb))
  out <- c(out, setpb(pb, 2.5))
  out <- c(out, getpb(pb))
  out <- c(out, setpb(pb, NA))
  out <- c(out, getpb(pb))
  out <- c(out, setpb(pb, 100))
  out <- c(out, getpb(pb))
  out <- c(out, setpb(pb, 5))
  out <- c(out, getpb(pb))
  closepb(pb)
  out
}

one <- function() {
  out <- numeric(0)
  opb <- pboptions(type = "timer")
  on.exit(pboptions(opb), add = TRUE)
  for (sty in 1:6) {
    out <- c(out, run_case(0, 10, initial = 0, style = sty, width = 35, char = "+"))
  }
  out <- c(out, run_case(0, 10, initial = 0.25, style = 3, width = 50, char = "."))
  out <- c(out, run_case(2, 5, initial = 2, style = 1, width = 0, char = "    "))
  out <- c(out, run_case(-10, 10, initial = -10, style = 5, width = 35, char = "[=-]"))
  out <- c(out, run_case(0, 1, initial = 0, style = 6, width = 50, char = "{*.}"))
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
