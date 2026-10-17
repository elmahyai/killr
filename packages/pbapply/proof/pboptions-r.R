suppressPackageStartupMessages(library(pbapply))
stopifnot(packageVersion("pbapply") == "1.7-5")
stopifnot(packageDescription("pbapply")$Version == "1.7-5")

numopts <- function(o) {
  c(
    as.numeric(o$style),
    as.numeric(o$txt.width),
    as.numeric(o$gui.width),
    as.numeric(o$initial),
    as.numeric(o$nout),
    as.numeric(o$min_time),
    as.numeric(o$use_lb)
  )
}

one <- function() {
  out <- numeric(0)
  opb <- pboptions(type = "txt", style = 1, char = ">", initial = 0.5, nout = 50)
  out <- c(out, numopts(opb))
  pb <- startpb(0, 10)
  out <- c(out, getpb(pb))
  closepb(pb)
  pboptions(style = 3, initial = 0.25)
  pb <- startpb(0, 10)
  out <- c(out, getpb(pb))
  closepb(pb)
  pboptions(opb)
  pb <- startpb(0, 10)
  if (!is.null(pb)) out <- c(out, getpb(pb))
  closepb(pb)
  out <- c(out, numopts(getOption("pboptions")))
  out
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- vapply(value, function(x) sprintf("%.17g", x), "")
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(parts, collapse = ","),
  median(elapsed) * 1000
))
