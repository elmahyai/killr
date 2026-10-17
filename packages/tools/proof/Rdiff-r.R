suppressPackageStartupMessages(library(tools))

one <- function() {
  dir <- tempfile("rdiff")
  dir.create(dir)
  a <- file.path(dir, "a.txt")
  b <- file.path(dir, "b.txt")
  c <- file.path(dir, "c.txt")
  d <- file.path(dir, "d.txt")
  e <- file.path(dir, "e.txt")
  f <- file.path(dir, "f.txt")
  writeLines(c("alpha", "beta  ", "gamma"), a)
  writeLines(c("alpha", "beta", "gamma"), b)
  writeLines(c("alpha", "BETA", "gamma"), c)
  writeLines("only", d)
  writeLines(c("see <environment: 0xabc> and <hashtable 1>", "\u2018q\u2019"), e)
  writeLines(c("see <environment: 0> and <hashtable output>", "'q'"), f)
  same <- Rdiff(a, b)
  diff_lines <- capture.output(diff_status <- Rdiff(a, c))
  len_msg <- capture.output(len_status <- Rdiff(a, d), type = "message")
  ptr <- Rdiff(e, f)
  paste0(
    "SAME ", same, "\n",
    "DIFF\n", paste(diff_lines, collapse="\n"), "\n", diff_status, "\n",
    "LEN ", paste(len_msg, collapse=" "), " ", len_status, "\n",
    "PTR ", ptr, "\n"
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
