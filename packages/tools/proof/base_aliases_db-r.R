suppressPackageStartupMessages(library(tools))

summarize <- function(x) {
  paste(vapply(names(x), function(pkg) {
    inner <- x[[pkg]]
    paste(vapply(names(inner), function(rd) paste(inner[[rd]], collapse = "\1"), ""), collapse = "\2")
  }, ""), collapse = "\3")
}

one <- function() {
  db <- base_aliases_db(verbose = FALSE, Ncpus = 1L)
  n_pkgs <- length(db)
  n_rd <- sum(vapply(db, length, 0L))
  n_alias <- sum(vapply(db, function(inner) sum(vapply(inner, length, 0L)), 0L))
  paste0(
    n_pkgs, "\n", n_rd, "\n", n_alias, "\n",
    nchar(summarize(db)), "\n",
    summarize(db), "\n"
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
