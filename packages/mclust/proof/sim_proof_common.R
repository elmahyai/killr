# Record writer and timer for the sim proofs (mclust 6.1.3). Run from packages/mclust:
#   Rscript proof/<name>-r.R
# Each case is list(id = <text>, run = <function returning a matrix or NULL>).
# The first case is the timed one. One untimed pass writes docs/output/<name>-r.txt,
# then the median of 20 timed calls (Sys.time) is written to proof/<name>-r-ms.txt.

sim_fmt <- function(x) sprintf("%.17g", x)  # NA prints as "NA" in sprintf

sim_record_lines <- function(id, m) {
  if (is.null(m)) return(c(paste0("case\t", id), "null\t1"))
  cn <- colnames(m)
  out <- c(paste0("case\t", id),
           paste0("dim\t", nrow(m), "\t", ncol(m)),
           paste0("colnames\t", if (is.null(cn)) "NULL" else paste(cn, collapse = ",")))
  for (i in seq_len(nrow(m))) {
    out <- c(out, paste(c("row", sim_fmt(as.numeric(m[i, ]))), collapse = "\t"))
  }
  out
}

# timed: optional function timed once per repetition; default is the first case's run.
sim_proof <- function(name, cases, timed = NULL) {
  res <- lapply(cases, function(cs) suppressWarnings(cs$run()))  # one untimed pass
  lines <- unlist(Map(function(cs, m) sim_record_lines(cs$id, m), cases, res),
                  use.names = FALSE)
  dir.create("docs/output", recursive = TRUE, showWarnings = FALSE)
  writeLines(lines, file.path("docs/output", paste0(name, "-r.txt")))
  main <- if (is.null(timed)) cases[[1]]$run else timed
  times <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- Sys.time()
    suppressWarnings(main())
    times[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
  }
  r_ms <- median(times)
  writeLines(sim_fmt(r_ms), file.path("proof", paste0(name, "-r-ms.txt")))
  cat(name, "R median ms:", r_ms, "\n")
  invisible(res)
}
